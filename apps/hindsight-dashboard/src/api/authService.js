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
    const response = await fetch(`${base()}/user-info`, {
      credentials: 'include', // Include cookies for authentication
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        // User is not authenticated
        return { authenticated: false };
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
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
