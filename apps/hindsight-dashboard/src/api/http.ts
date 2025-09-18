// Centralized HTTP helpers for consistent API URL handling

const getCookie = (name: string): string | null => {
  if (typeof document === 'undefined') return null;
  try {
    const cookies = document.cookie ? document.cookie.split(';') : [];
    for (const entry of cookies) {
      const [rawKey, ...rest] = entry.split('=');
      if (!rawKey) continue;
      if (rawKey.trim() === name) {
        const value = rest.join('=');
        return value ? decodeURIComponent(value) : '';
      }
    }
  } catch {}
  return null;
};

export const isGuest = (): boolean => {
  try {
    return typeof window !== 'undefined' && sessionStorage.getItem('GUEST_MODE') === 'true';
  } catch {
    return false;
  }
};

const shouldUseLocalFallback = (): boolean => {
  if (typeof window === 'undefined') return false;
  try {
    const hostname = window.location.hostname?.toLowerCase();
    if (!hostname) return false;
    return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === 'host.docker.internal' || hostname === '::1';
  } catch {
    return false;
  }
};

// Resolve base path: '/api' or '/guest-api', or provided overrides
export const apiBasePath = (): string => {
  try {
    const runtime = (typeof window !== 'undefined' && (window as any).__ENV__?.HINDSIGHT_SERVICE_API_URL) || null;
    const build = (typeof process !== 'undefined' && (process as any).env?.VITE_HINDSIGHT_SERVICE_API_URL) || null;
    const base = runtime || build || '/api';
    // If base is an absolute URL (http/https), keep it as-is for both guest and auth.
    // Only switch to "/guest-api" when we're using relative, same-origin proxying.
    if (/^https?:\/\//i.test(base)) return base;
    return isGuest() ? '/guest-api' : base;
  } catch {
    return isGuest() ? '/guest-api' : '/api';
  }
};

// Absolute base URL (no trailing slash), resolved against current origin
export const apiBase = (): string => {
  let basePath = apiBasePath();
  
  try {
    if (typeof window !== 'undefined') {
      // If we have an absolute URL, upgrade http to https if the app is running on https
      if (/^https?:\/\//i.test(basePath)) {
        const isHttps = window.location.protocol === 'https:';
        const url = new URL(basePath);
        if (isHttps && url.protocol === 'http:') {
          url.protocol = 'https:';
          basePath = url.toString();
        }
      }
      const result = new URL(basePath, window.location.origin).toString().replace(/\/$/, '');
      return result;
    }
  } catch {}
  return basePath.replace(/\/$/, '');
};

// Build absolute URL for a given path (ensures leading slash)
export const apiUrl = (path: string): string => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${apiBase()}${cleanPath}`;
};

// As above but ensures trailing slash (useful for list endpoints to avoid redirects)
export const apiUrlDir = (path: string): string => {
  const u = apiUrl(path);
  return u.endsWith('/') ? u : `${u}/`;
};

export type ApiFetchInit = RequestInit & {
  searchParams?: Record<string, any> | URLSearchParams;
  ensureTrailingSlash?: boolean;
  noScope?: boolean; // opt out of automatic scope injection
  scopeOverride?: { scope: 'personal' | 'organization' | 'public'; organizationId?: string | null };
};

export const apiFetch = async (path: string, init: ApiFetchInit = {}): Promise<Response> => {
  const { searchParams, ensureTrailingSlash, noScope, scopeOverride, ...rest } = init;
  let url = ensureTrailingSlash ? apiUrlDir(path) : apiUrl(path);

  // Start with provided params
  const usp = searchParams instanceof URLSearchParams ? new URLSearchParams(searchParams.toString()) : new URLSearchParams();
  if (searchParams && !(searchParams instanceof URLSearchParams)) {
    for (const [k, v] of Object.entries(searchParams)) {
      if (v !== undefined && v !== null) usp.append(k, String(v));
    }
  }

  // Inject scope/org for ALL methods by default, unless noScope=true
  const method = (rest.method || 'GET').toUpperCase();
  let activeScope: string | undefined;
  let activeOrgId: string | undefined;
  if (!noScope) {
    try {
      // Respect explicit override first
      if (scopeOverride?.scope) {
        activeScope = scopeOverride.scope;
        if (scopeOverride.scope === 'organization' && scopeOverride.organizationId) {
          activeOrgId = scopeOverride.organizationId || undefined;
        }
      } else {
        activeScope = sessionStorage.getItem('ACTIVE_SCOPE') || undefined;
        if (!activeScope && isGuest()) activeScope = 'public';
        activeOrgId = sessionStorage.getItem('ACTIVE_ORG_ID') || undefined;
      }

      // Add query params for compatibility
      if (activeScope) usp.set('scope', activeScope);
      if (activeScope === 'organization' && activeOrgId) usp.set('organization_id', activeOrgId);
    } catch {}
  }

  if ([...usp.keys()].length > 0) {
    const sep = url.includes('?') ? '&' : '?';
    url = `${url}${sep}${usp.toString()}`;
  }

  // Merge headers with scope headers
  // Merge headers while preserving original casing (important for tests that access headers via object keys)
  const headersObj: Record<string, string> = {};
  const src = (rest.headers as any);
  if (src) {
    if (typeof src.forEach === 'function') {
      try { src.forEach((v: string, k: string) => { headersObj[k] = v; }); } catch {}
    } else if (Array.isArray(src)) {
      for (const [k, v] of src) { headersObj[k as string] = String(v); }
    } else if (typeof src === 'object') {
      for (const k of Object.keys(src)) { headersObj[k] = String((src as any)[k]); }
    }
  }
  if (!noScope && activeScope) {
    headersObj['X-Active-Scope'] = activeScope;
    if (activeScope === 'organization' && activeOrgId) {
      headersObj['X-Organization-Id'] = activeOrgId;
    }
  }

  // In dev mode, attach oauth2-proxy header shim so backend treats requests as authenticated.
  if (typeof window !== 'undefined') {
    const { devModeHeaders } = await import('../utils/devMode');
    const implicitHeaders = devModeHeaders();
    if (Object.keys(implicitHeaders).length > 0 && typeof console !== 'undefined' && console.debug) {
      console.debug('[apiFetch] attaching dev auth headers', implicitHeaders);
    }
    for (const key of Object.keys(implicitHeaders)) {
      if (!headersObj[key]) headersObj[key] = implicitHeaders[key];
    }
  }

  const methodNeedsCsrf = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);
  if (methodNeedsCsrf) {
    // Forward oauth2-proxy CSRF token for write operations when present
    const hasCsrfHeader = Object.keys(headersObj).some((key) => key.toLowerCase() === 'x-csrf-token');
    if (!hasCsrfHeader) {
      const token = getCookie('_oauth2_proxy_csrf');
      if (token) headersObj['X-CSRF-Token'] = token;
    }
  }

  // Dev-time guardrails: warn on writes without scope
  const __DEV__ = (() => { try { return (typeof process !== 'undefined' && (process as any).env && (process as any).env.NODE_ENV !== 'production'); } catch { return false; } })();
  if (__DEV__) {
    const isWrite = !['GET', 'HEAD', 'OPTIONS'].includes(method);
    if (isWrite && !noScope && !activeScope) {
      // eslint-disable-next-line no-console
      console.warn('[apiFetch] write without active scope');
    }
  }

  const req: RequestInit = { credentials: 'include', ...rest, headers: headersObj };

  const allowLocalFallback = shouldUseLocalFallback();

  try {
    const res = await fetch(url, req);
    // If backend is unreachable via proxy (/api) in local dev, try direct fallbacks.
    if (
      allowLocalFallback &&
      !res.ok &&
      res.status === 502 &&
      (apiBasePath() === '/api' || apiBasePath() === '/guest-api')
    ) {
      // Try localhost and host.docker.internal fallbacks
      const candidates = ['http://localhost:8000', 'http://127.0.0.1:8000', 'http://host.docker.internal:8000'];
      for (const base of candidates) {
        try {
          const directUrl = (ensureTrailingSlash ? `${base}${path}`.replace(/([^/])$/, '$1/') : `${base}${path}`);
          const res2 = await fetch(directUrl, req);
          if (res2.ok || res2.status !== 502) return res2;
        } catch {}
      }
    }
    return res;
  } catch (e) {
    // Network error: attempt direct fallbacks in dev scenario
    if (
      allowLocalFallback &&
      (apiBasePath() === '/api' || apiBasePath() === '/guest-api')
    ) {
      const candidates = ['http://localhost:8000', 'http://127.0.0.1:8000', 'http://host.docker.internal:8000'];
      for (const base of candidates) {
        try {
          const directUrl = (ensureTrailingSlash ? `${base}${path}`.replace(/([^/])$/, '$1/') : `${base}${path}`);
          const res2 = await fetch(directUrl, req);
          return res2;
        } catch {}
      }
    }
    throw e;
  }
};
