// Prefer runtime env first; fall back to build-time env or relative '/api'
let API_BASE_URL = (
  typeof window !== 'undefined' && window.__ENV__ && window.__ENV__.HINDSIGHT_SERVICE_API_URL
) || import.meta.env.VITE_HINDSIGHT_SERVICE_API_URL || '/api';

const isGuest = () => {
  try { return sessionStorage.getItem('GUEST_MODE') === 'true'; } catch { return false; }
};

const base = () => (isGuest() ? '/guest-api' : API_BASE_URL);

// Upgrade API scheme at runtime to avoid mixed content in prod
try {
  if (typeof window !== 'undefined' && API_BASE_URL) {
    const isHttps = window.location.protocol === 'https:';
    const url = new URL(API_BASE_URL);
    if (isHttps && url.protocol === 'http:') {
      url.protocol = 'https:';
      API_BASE_URL = url.toString().replace(/\/$/, '');
    }
  }
} catch (_) {
  // Ignore URL parsing issues; fall back to provided env value
}

// When using relative '/api', this remains same-origin via Nginx proxy

const authService = {
  // Get current user info from OAuth2 proxy
  getCurrentUser: async () => {
    try {
      // Always hit the authenticated path to let oauth2-proxy set cookies/headers.
      // Using '/api' avoids being trapped in guest mode due to sessionStorage.
      const response = await fetch(`/api/user-info`, {
        credentials: 'include',
        redirect: 'follow',
      });
      // If unauthenticated and behind oauth2-proxy reverse-proxy, some setups
      // issue a 302 to the provider, which will fail CORS in fetch. We try to
      // detect clean 401 here; otherwise, callers treat errors as unauthenticated.
      if (!response.ok) {
        if (response.status === 401) {
          return { authenticated: false };
        }
        // For other statuses, treat as unauthenticated rather than throwing
        return { authenticated: false };
      }
      return await response.json();
    } catch (_) {
      // On network/CORS/redirect issues, do not spam errors; just report not authenticated
      return { authenticated: false };
    }
  },

  // Check if user is authenticated
  isAuthenticated: async () => {
    try {
      const userInfo = await authService.getCurrentUser();
      return userInfo.authenticated;
    } catch (error) {
      console.error('Error checking authentication:', error);
      return false;
    }
  }
};

export default authService;
