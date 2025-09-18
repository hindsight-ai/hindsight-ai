import { apiFetch } from './http';

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
  beta_access_status?: 'not_requested' | 'pending' | 'accepted' | 'denied' | 'revoked';
  beta_access_admin?: boolean;
  memberships?: OrganizationMembership[];
  llm_features_enabled?: boolean;
}

const authService = {
  getCurrentUser: async (): Promise<CurrentUserInfo> => {
    try {
      const response = await apiFetch('/user-info', { credentials: 'include' });
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
