// Centralized HTTP helpers for consistent API URL handling

import { getScope } from './scopeProvider';
import { ApiError, AuthenticationError, AuthorizationError, NetworkError } from './errors';

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

// Internal: resolve relative base path ('/api' or '/guest-api', or env override).
const resolveBasePath = (): string => {
  try {
    const runtime = (typeof window !== 'undefined' && (window as any).__ENV__?.HINDSIGHT_SERVICE_API_URL) || null;
    const build = (typeof process !== 'undefined' && (process as any).env?.VITE_HINDSIGHT_SERVICE_API_URL) || null;
    const base = runtime || build || '/api';
    // Absolute URL stays as-is for both guest and auth.
    // Only switch to "/guest-api" when using relative, same-origin proxying.
    if (/^https?:\/\//i.test(base)) return base;
    return isGuest() ? '/guest-api' : base;
  } catch {
    return isGuest() ? '/guest-api' : '/api';
  }
};

// Internal: absolute base URL (no trailing slash), resolved against current origin.
const resolveAbsoluteBase = (): string => {
  let basePath = resolveBasePath();
  try {
    if (typeof window !== 'undefined') {
      // Upgrade http→https on https origin to avoid mixed-content blocks.
      if (/^https?:\/\//i.test(basePath)) {
        const isHttps = window.location.protocol === 'https:';
        const url = new URL(basePath);
        if (isHttps && url.protocol === 'http:') {
          url.protocol = 'https:';
          basePath = url.toString();
        }
      }
      return new URL(basePath, window.location.origin).toString().replace(/\/$/, '');
    }
  } catch {}
  return basePath.replace(/\/$/, '');
};

// Canonical URL builder. Accepts paths with or without leading slash.
// Pass `{ trailingSlash: true }` for list endpoints that must end in `/`.
export const apiUrl = (path: string, opts?: { trailingSlash?: boolean }): string => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${resolveAbsoluteBase()}${cleanPath}`;
  if (opts?.trailingSlash && !url.endsWith('/')) return `${url}/`;
  return url;
};

export type ApiFetchInit = RequestInit & {
  searchParams?: Record<string, any> | URLSearchParams;
  ensureTrailingSlash?: boolean;
  noScope?: boolean; // opt out of automatic scope injection
  scopeOverride?: { scope: 'personal' | 'organization' | 'public'; organizationId?: string | null };
};

export const apiFetch = async (path: string, init: ApiFetchInit = {}): Promise<Response> => {
  const { searchParams, ensureTrailingSlash, noScope, scopeOverride, ...rest } = init;
  let url = apiUrl(path, { trailingSlash: ensureTrailingSlash });

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
        const snapshot = getScope();
        activeScope = snapshot.scope;
        if (!activeScope && isGuest()) activeScope = 'public';
        activeOrgId = snapshot.orgId;
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

  const throwTypedError = (res: Response): never => {
    if (res.status === 401) throw new AuthenticationError();
    if (res.status === 403) throw new AuthorizationError();
    throw new ApiError(res.status, `HTTP error ${res.status}`);
  };

  try {
    const res = await fetch(url, req);
    // If backend is unreachable via proxy (/api) in local dev, try direct fallbacks.
    if (
      allowLocalFallback &&
      !res.ok &&
      res.status === 502 &&
      (resolveBasePath() === '/api' || resolveBasePath() === '/guest-api')
    ) {
      // Try localhost and host.docker.internal fallbacks
      const candidates = ['http://localhost:8000', 'http://127.0.0.1:8000', 'http://host.docker.internal:8000'];
      for (const base of candidates) {
        try {
          const directUrl = (ensureTrailingSlash ? `${base}${path}`.replace(/([^/])$/, '$1/') : `${base}${path}`);
          const res2 = await fetch(directUrl, req);
          if (res2.ok || res2.status !== 502) {
            if (!res2.ok) throwTypedError(res2);
            return res2;
          }
        } catch (fallbackErr) {
          if (fallbackErr instanceof ApiError || fallbackErr instanceof AuthenticationError || fallbackErr instanceof AuthorizationError) throw fallbackErr;
        }
      }
    }
    if (!res.ok) throwTypedError(res);
    return res;
  } catch (e) {
    // Network error: attempt direct fallbacks in dev scenario
    if (
      e instanceof TypeError &&
      allowLocalFallback &&
      (resolveBasePath() === '/api' || resolveBasePath() === '/guest-api')
    ) {
      const candidates = ['http://localhost:8000', 'http://127.0.0.1:8000', 'http://host.docker.internal:8000'];
      for (const base of candidates) {
        try {
          const directUrl = (ensureTrailingSlash ? `${base}${path}`.replace(/([^/])$/, '$1/') : `${base}${path}`);
          const res2 = await fetch(directUrl, req);
          if (!res2.ok) throwTypedError(res2);
          return res2;
        } catch (fallbackErr) {
          if (fallbackErr instanceof ApiError || fallbackErr instanceof AuthenticationError || fallbackErr instanceof AuthorizationError) throw fallbackErr;
        }
      }
    }
    // Wrap raw TypeError fetch failures as NetworkError; re-throw typed errors as-is
    if (e instanceof ApiError || e instanceof AuthenticationError || e instanceof AuthorizationError || e instanceof NetworkError) throw e;
    throw new NetworkError(e instanceof Error ? e.message : 'Network error', e);
  }
};
