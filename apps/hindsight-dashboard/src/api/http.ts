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
};

export const apiFetch = (path: string, init: ApiFetchInit = {}): Promise<Response> => {
  const { searchParams, ensureTrailingSlash, ...rest } = init;
  let url = ensureTrailingSlash ? apiUrlDir(path) : apiUrl(path);

  if (searchParams) {
    const usp = searchParams instanceof URLSearchParams ? searchParams : new URLSearchParams();
    if (!(searchParams instanceof URLSearchParams)) {
      for (const [k, v] of Object.entries(searchParams)) {
        if (v !== undefined && v !== null) usp.append(k, String(v));
      }
    }
    const sep = url.includes('?') ? '&' : '?';
    url = `${url}${sep}${usp.toString()}`;
  }

  const req: RequestInit = { credentials: 'include', ...rest };
  return fetch(url, req);
};

