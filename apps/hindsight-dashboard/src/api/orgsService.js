// Prefer runtime env first; fall back to process env or relative '/api'
let API_BASE_URL = '/api';
try {
  if (typeof window !== 'undefined' && window.__ENV__ && window.__ENV__.HINDSIGHT_SERVICE_API_URL) {
    API_BASE_URL = window.__ENV__.HINDSIGHT_SERVICE_API_URL;
  } else if (typeof process !== 'undefined' && process.env && process.env.VITE_HINDSIGHT_SERVICE_API_URL) {
    API_BASE_URL = process.env.VITE_HINDSIGHT_SERVICE_API_URL;
  }
} catch {}

// Upgrade API scheme at runtime to avoid mixed content when app is served over HTTPS
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

const isGuest = () => {
  try { return sessionStorage.getItem('GUEST_MODE') === 'true'; } catch { return false; }
};
const base = () => (isGuest() ? '/guest-api' : API_BASE_URL);

const orgsService = {
  listOrganizations: async () => {
    const resp = await fetch(`${base()}/organizations/`, { credentials: 'include' });
    if (!resp.ok) {
      if (resp.status === 401) return []; // unauth → no orgs
      throw new Error(`HTTP ${resp.status}`);
    }
    return resp.json();
  },
};

export default orgsService;

