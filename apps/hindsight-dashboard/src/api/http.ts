// Centralized HTTP helpers for consistent API URL handling

export const isGuest = (): boolean => {
  try {
    return typeof window !== 'undefined' && sessionStorage.getItem('GUEST_MODE') === 'true';
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
      if (basePath.startsWith('http')) {
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
};

export const apiFetch = (path: string, init: ApiFetchInit = {}): Promise<Response> => {
  const { searchParams, ensureTrailingSlash, noScope, ...rest } = init;
  let url = ensureTrailingSlash ? apiUrlDir(path) : apiUrl(path);

  // Start with provided params
  const usp = searchParams instanceof URLSearchParams ? new URLSearchParams(searchParams.toString()) : new URLSearchParams();
  if (searchParams && !(searchParams instanceof URLSearchParams)) {
    for (const [k, v] of Object.entries(searchParams)) {
      if (v !== undefined && v !== null) usp.append(k, String(v));
    }
  }

  // Inject scope/org for GET/HEAD by default, unless noScope=true
  const method = (rest.method || 'GET').toUpperCase();
  if (!noScope && (method === 'GET' || method === 'HEAD')) {
    try {
      const existingScope = usp.get('scope');
      const existingOrg = usp.get('organization_id');
      let scope = existingScope;
      let orgId = existingOrg;

      if (!scope) {
        scope = sessionStorage.getItem('ACTIVE_SCOPE') || undefined;
        if (!scope && isGuest()) scope = 'public';
      }
      if (!orgId) {
        orgId = sessionStorage.getItem('ACTIVE_ORG_ID') || undefined;
      }
      if (scope) usp.set('scope', scope);
      if (scope === 'organization' && orgId) usp.set('organization_id', orgId);
    } catch {}
  }

  if ([...usp.keys()].length > 0) {
    const sep = url.includes('?') ? '&' : '?';
    url = `${url}${sep}${usp.toString()}`;
  }

  const req: RequestInit = { credentials: 'include', ...rest };
  return fetch(url, req);
};
