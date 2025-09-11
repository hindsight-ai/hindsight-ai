// Prefer runtime env first; fall back to process env or relative '/api'
let API_BASE_URL: string = '/api';
try {
  if (typeof window !== 'undefined' && (window as any).__ENV__?.HINDSIGHT_SERVICE_API_URL) {
    API_BASE_URL = (window as any).__ENV__.HINDSIGHT_SERVICE_API_URL;
  } else if (typeof process !== 'undefined' && process.env?.VITE_HINDSIGHT_SERVICE_API_URL) {
    API_BASE_URL = process.env.VITE_HINDSIGHT_SERVICE_API_URL;
  }
} catch {}

const isGuest = (): boolean => {
  try { return sessionStorage.getItem('GUEST_MODE') === 'true'; } catch { return false; }
};

const base = () => {
  const relativeUrl = isGuest() ? '/guest-api' : API_BASE_URL;
  
  // Convert to absolute URL to avoid browser base URL resolution issues
  let absoluteUrl;
  if (typeof window !== 'undefined') {
    // In development, ensure we use the correct port
    const currentOrigin = window.location.origin;
    const isDev = currentOrigin.includes(':3000');
    
    if (isDev) {
      absoluteUrl = `http://localhost:3000${relativeUrl}`;
    } else {
      // In production, use current origin
      absoluteUrl = `${currentOrigin}${relativeUrl}`;
    }
  } else {
    // Fallback for non-browser environments
    absoluteUrl = relativeUrl;
  }
  
  console.log(`[DEBUG] authService base URL: ${absoluteUrl} original: ${relativeUrl} origin: ${typeof window !== 'undefined' ? window.location.origin : 'unknown'}`);
  
  return absoluteUrl;
};

export interface OrganizationMembership {
  id?: string;
  organization_id: string;
  organization_name?: string;
  role?: string; // owner|admin|editor|viewer
  can_read?: boolean;
  can_write?: boolean;
}

export interface CurrentUserInfo {
  authenticated: boolean;
  user_id?: string;
  email?: string;
  display_name?: string;
  is_superadmin?: boolean;
  memberships?: OrganizationMembership[];
}

const authService = {
  getCurrentUser: async (): Promise<CurrentUserInfo> => {
    try {
      const response = await fetch(`${base()}/user-info`, { credentials: 'include', redirect: 'follow' });
      if (!response.ok) {
        if (response.status === 401) {
          return { authenticated: false };
        }
        return { authenticated: false };
      }
      return await response.json();
    } catch {
      return { authenticated: false };
    }
  },
  isAuthenticated: async (): Promise<boolean> => {
    try { const userInfo = await authService.getCurrentUser(); return !!userInfo.authenticated; } catch { return false; }
  }
};

export default authService;
