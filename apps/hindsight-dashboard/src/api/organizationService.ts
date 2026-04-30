import authService from './authService';
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

export interface OrganizationInvitation {
  id: string;
  organization_id: string;
  invited_by_user_id: string;
  email: string;
  role: string;
  status: string;
  token?: string | null;
  created_at: string;
  expires_at: string;
  accepted_at?: string | null;
  revoked_at?: string | null;
}

const organizationService = {
  // Get all organizations for current user
  getOrganizations: async (): Promise<Organization[]> => {
    const response = await apiFetch('/organizations/', { ensureTrailingSlash: true });
    return await response.json();
  },

  // Get organizations that the user can manage (own/admin role for regular users, all for superadmins)
  getManageableOrganizations: async (): Promise<Organization[]> => {
    const response = await apiFetch('/organizations/manageable');
    return await response.json();
  },

  // Get all organizations for administration (superadmin only)
  getOrganizationsAdmin: async (): Promise<Organization[]> => {
    const response = await apiFetch('/organizations/admin');
    return await response.json();
  },

  // Get specific organization
  getOrganization: async (orgId: string): Promise<Organization> => {
    const response = await apiFetch(`/organizations/${orgId}`);
    return await response.json();
  },

  // Create new organization
  createOrganization: async (data: CreateOrganizationData): Promise<Organization> => {
    const response = await apiFetch('/organizations/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return await response.json();
  },

  // Update organization
  updateOrganization: async (orgId: string, data: Partial<CreateOrganizationData>): Promise<Organization> => {
    const response = await apiFetch(`/organizations/${orgId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return await response.json();
  },

  // Delete organization
  deleteOrganization: async (orgId: string): Promise<void> => {
    await apiFetch(`/organizations/${orgId}`, { method: 'DELETE' });
  },

  // Get organization members
  getMembers: async (orgId: string): Promise<OrganizationMember[]> => {
    const response = await apiFetch(`/organizations/${orgId}/members`);
    return await response.json();
  },

  // Add member to organization
  addMember: async (orgId: string, memberData: { email: string; role: string }): Promise<OrganizationMember> => {
    const response = await apiFetch(`/organizations/${orgId}/members`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(memberData),
    });
    return await response.json();
  },

  // Update member role/permissions
  updateMember: async (orgId: string, userId: string, data: UpdateMemberData): Promise<void> => {
    await apiFetch(`/organizations/${orgId}/members/${userId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
  },

  // Remove member from organization
  removeMember: async (orgId: string, userId: string): Promise<void> => {
    await apiFetch(`/organizations/${orgId}/members/${userId}`, { method: 'DELETE' });
  },

  // Invitations: accept
  acceptInvitation: async (orgId: string, invitationId: string, token?: string): Promise<void> => {
    const url = token ? `/organizations/${orgId}/invitations/${invitationId}/accept?token=${encodeURIComponent(token)}` : `/organizations/${orgId}/invitations/${invitationId}/accept`;
    await apiFetch(url, { method: 'POST' });
  },

  // Invitations: decline
  declineInvitation: async (orgId: string, invitationId: string, token?: string): Promise<void> => {
    const url = token ? `/organizations/${orgId}/invitations/${invitationId}/decline?token=${encodeURIComponent(token)}` : `/organizations/${orgId}/invitations/${invitationId}/decline`;
    await apiFetch(url, { method: 'POST' });
  },

  // Invitations: list
  listInvitations: async (orgId: string, status: string = 'pending'): Promise<OrganizationInvitation[]> => {
    const response = await apiFetch(`/organizations/${orgId}/invitations`, { searchParams: { status } });
    return await response.json();
  },

  // Invitations: create
  createInvitation: async (orgId: string, data: { email: string; role: string }): Promise<OrganizationInvitation> => {
    const response = await apiFetch(`/organizations/${orgId}/invitations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return await response.json();
  },

  // Invitations: resend
  resendInvitation: async (orgId: string, invitationId: string): Promise<OrganizationInvitation> => {
    const response = await apiFetch(`/organizations/${orgId}/invitations/${invitationId}/resend`, { method: 'POST' });
    return await response.json();
  },

  // Invitations: revoke (delete)
  revokeInvitation: async (orgId: string, invitationId: string): Promise<void> => {
    await apiFetch(`/organizations/${orgId}/invitations/${invitationId}`, { method: 'DELETE' });
  },
};

export default organizationService;
