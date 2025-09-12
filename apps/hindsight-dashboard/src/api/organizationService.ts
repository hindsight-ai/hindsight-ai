import authService from './authService';
import notificationService from '../services/notificationService';
import { apiFetch } from './http';

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
      const response = await apiFetch('/organizations/', { ensureTrailingSlash: true });
      
      if (!response.ok) {
        console.error('Error fetching organizations:', `HTTP error ${response.status}`);
        
        // Handle specific error cases without showing notifications for 401
        // (401 is handled by auth interceptor and shows its own notification)
        if (response.status !== 401) {
          notificationService.showApiError(response.status, undefined, 'fetch organizations');
        }
        
        throw new Error(`HTTP error ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching organizations:', error);
      
      // Handle network errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        notificationService.showNetworkError();
      }
      
      throw error;
    }
  },

  // Get organizations that the user can manage (own/admin role for regular users, all for superadmins)
  getManageableOrganizations: async (): Promise<Organization[]> => {
    try {
      const response = await apiFetch('/organizations/manageable');
      
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching manageable organizations:', error);
      throw error;
    }
  },

  // Get all organizations for administration (superadmin only)
  getOrganizationsAdmin: async (): Promise<Organization[]> => {
    try {
      const response = await apiFetch('/organizations/admin');
      
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
      const response = await apiFetch(`/organizations/${orgId}`);
      
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
      const response = await apiFetch('/organizations/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error creating organization:', errorText);
        
        // Show appropriate toast notification based on status
        notificationService.showApiError(response.status, errorText, 'create organization');
        
        throw new Error(`HTTP error ${response.status}: ${errorText}`);
      }
      
      // Show success notification
      notificationService.showSuccess('Organization created successfully!');
      return await response.json();
    } catch (error) {
      console.error('Error creating organization:', error);
      
      // Handle network errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        notificationService.showNetworkError();
      } else if (error instanceof Error && !error.message.includes('HTTP error')) {
        // Only show generic error if we haven't already shown a specific one
        notificationService.showError('Failed to create organization. Please try again.');
      }
      
      throw error;
    }
  },

  // Update organization
  updateOrganization: async (orgId: string, data: Partial<CreateOrganizationData>): Promise<Organization> => {
    try {
      const response = await apiFetch(`/organizations/${orgId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
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
      const response = await apiFetch(`/organizations/${orgId}`, { method: 'DELETE' });
      
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
      const response = await apiFetch(`/organizations/${orgId}/members`);
      
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
      const response = await apiFetch(`/organizations/${orgId}/members`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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
      const response = await apiFetch(`/organizations/${orgId}/members/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
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
      const response = await apiFetch(`/organizations/${orgId}/members/${userId}`, { method: 'DELETE' });
      
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
