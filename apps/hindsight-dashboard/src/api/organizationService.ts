import authService from './authService';

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
    absoluteUrl = relativeUrl; // Fallback for server-side rendering
  }
  
  console.log('[DEBUG] organizationService base URL:', absoluteUrl, 'original:', relativeUrl, 'origin:', typeof window !== 'undefined' ? window.location.origin : 'N/A');
  return absoluteUrl;
};

export interface Organization {
  id: string;
  name: string;
  slug?: string;
  is_active: boolean;
}

export interface OrganizationMember {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  can_read: boolean;
  can_write: boolean;
}

export interface CreateOrganizationData {
  name: string;
  slug?: string;
}

export interface AddMemberData {
  email: string;
  role: string;
  can_read?: boolean;
  can_write?: boolean;
}

export interface UpdateMemberData {
  role?: string;
  can_read?: boolean;
  can_write?: boolean;
}

const organizationService = {
  // Get all organizations for current user
  getOrganizations: async (): Promise<Organization[]> => {
    try {
      const response = await fetch(`${base()}/organizations/`, {
        method: 'GET',
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching organizations:', error);
      throw error;
    }
  },

  // Get all organizations for administration (superadmin only)
  getOrganizationsAdmin: async (): Promise<Organization[]> => {
    try {
      const response = await fetch(`${base()}/organizations/admin`, {
        method: 'GET',
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching organizations for admin:', error);
      throw error;
    }
  },

  // Get specific organization
  getOrganization: async (orgId: string): Promise<Organization> => {
    try {
      const response = await fetch(`${base()}/organizations/${orgId}`, {
        method: 'GET',
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching organization:', error);
      throw error;
    }
  },

  // Create new organization
  createOrganization: async (data: CreateOrganizationData): Promise<Organization> => {
    try {
      const response = await fetch(`${base()}/organizations/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`HTTP error ${response.status}: ${error}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error creating organization:', error);
      throw error;
    }
  },

  // Update organization
  updateOrganization: async (orgId: string, data: Partial<CreateOrganizationData>): Promise<Organization> => {
    try {
      const response = await fetch(`${base()}/organizations/${orgId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`HTTP error ${response.status}: ${error}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error updating organization:', error);
      throw error;
    }
  },

  // Delete organization
  deleteOrganization: async (orgId: string): Promise<void> => {
    try {
      const response = await fetch(`${base()}/organizations/${orgId}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
    } catch (error) {
      console.error('Error deleting organization:', error);
      throw error;
    }
  },

  // Get organization members
  getMembers: async (orgId: string): Promise<OrganizationMember[]> => {
    try {
      const response = await fetch(`${base()}/organizations/${orgId}/members`, {
        method: 'GET',
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching organization members:', error);
      throw error;
    }
  },

  // Add member to organization
  addMember: async (orgId: string, memberData: { email: string; role: string }): Promise<OrganizationMember> => {
    try {
      const response = await fetch(`${base()}/organizations/${orgId}/members`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(memberData),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`HTTP error ${response.status}: ${error}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error adding organization member:', error);
      throw error;
    }
  },

  // Update member role/permissions
  updateMember: async (orgId: string, userId: string, data: UpdateMemberData): Promise<void> => {
    try {
      const response = await fetch(`${base()}/organizations/${orgId}/members/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`HTTP error ${response.status}: ${error}`);
      }
    } catch (error) {
      console.error('Error updating organization member:', error);
      throw error;
    }
  },

  // Remove member from organization
  removeMember: async (orgId: string, userId: string): Promise<void> => {
    try {
      const response = await fetch(`${base()}/organizations/${orgId}/members/${userId}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
    } catch (error) {
      console.error('Error removing organization member:', error);
      throw error;
    }
  },
};

export default organizationService;
