let API_BASE_URL: string = '/api';
try {
  if (typeof window !== 'undefined' && (window as any).__ENV__?.HINDSIGHT_SERVICE_API_URL) {
    API_BASE_URL = (window as any).__ENV__.HINDSIGHT_SERVICE_API_URL;
  } else if (typeof process !== 'undefined' && process.env?.VITE_HINDSIGHT_SERVICE_API_URL) {
    API_BASE_URL = process.env.VITE_HINDSIGHT_SERVICE_API_URL;
  }
} catch {}

try {
  if (typeof window !== 'undefined' && API_BASE_URL) {
    const isHttps = window.location.protocol === 'https:';
    const url = new URL(API_BASE_URL, window.location.origin);
    if (isHttps && url.protocol === 'http:') {
      url.protocol = 'https:';
      API_BASE_URL = url.toString().replace(/\/$/, '');
    }
  }
} catch {}

const isGuest = (): boolean => { try { return sessionStorage.getItem('GUEST_MODE') === 'true'; } catch { return false; } };
const base = () => (isGuest() ? '/guest-api' : API_BASE_URL);

export interface OrganizationSummary {
  id: string;
  name: string;
  slug?: string;
  role?: string;
}

const orgsService = {
  listOrganizations: async (): Promise<OrganizationSummary[]> => {
    const resp = await fetch(`${base()}/organizations/`, { credentials: 'include' });
    if (!resp.ok) {
      if (resp.status === 401) return [];
      throw new Error(`HTTP ${resp.status}`);
    }
    return resp.json();
  },
};

export default orgsService;
