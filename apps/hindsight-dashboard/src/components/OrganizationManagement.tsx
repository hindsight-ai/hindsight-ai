import React, { useState, useEffect } from 'react';
import Portal from './Portal';
import { useAuth } from '../context/AuthContext';
import { useOrganization } from '../context/OrganizationContext';
import organizationService, { Organization, OrganizationMember, CreateOrganizationData, AddMemberData, OrganizationInvitation } from '../api/organizationService';
import notificationService from '../services/notificationService';
import { apiFetch } from '../api/http';

interface OrganizationManagementProps {
  onClose: () => void;
}

const OrganizationManagement: React.FC<OrganizationManagementProps> = ({ onClose }) => {
  const { user, refresh: refreshUser } = useAuth();
  const { refreshOrganizations } = useOrganization();
  const [allOrganizations, setAllOrganizations] = useState<Organization[]>([]);

  // Enhanced close handler that refreshes organization dropdown
  const handleClose = async () => {
    try {
      // Refresh organization dropdown to show new organizations immediately
      await refreshOrganizations();
    } catch (error) {
      // Don't block closing if refresh fails, but log the error
      console.error('Failed to refresh organizations on close:', error);
    }
    onClose();
  };
  const [userMemberOrganizations, setUserMemberOrganizations] = useState<Organization[]>([]);
  // Non-superadmin users are always in 'member' mode
  const [viewMode, setViewMode] = useState<'member' | 'all'>('member');
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>([]);
  const [invitationFilter, setInvitationFilter] = useState<'pending'|'accepted'|'revoked'|'expired'|'all'>('pending');
  const [invCounts, setInvCounts] = useState<{pending:number; accepted:number; revoked:number; expired:number}>({pending:0,accepted:0,revoked:0,expired:0});
  const [auditOpen, setAuditOpen] = useState<{open:boolean; invitationId?:string}>({open:false});
  const [loading, setLoading] = useState(true);
  const [createMode, setCreateMode] = useState(false);
  const [newOrgData, setNewOrgData] = useState<CreateOrganizationData>({ name: '', slug: '' });
  const [addMemberMode, setAddMemberMode] = useState(false);
  const [newMemberData, setNewMemberData] = useState<AddMemberData>({ email: '', role: 'viewer' });
  const [inviteMode, setInviteMode] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('viewer');
  const [showModeConfirmation, setShowModeConfirmation] = useState(false);
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);

  // Check if user has access to organization management
  // Users can access org management if they are authenticated:
  // 1. Superadmins (can manage all organizations), OR
  // 2. Regular authenticated users (can create organizations and manage ones where they have owner/admin roles)
  const hasAccess = user?.authenticated === true;  // Check if user is a member of an organization
  const isUserMember = (orgId: string): boolean => {
    return userMemberOrganizations.some(org => org.id === orgId);
  };

  // Get organizations to display based on current view mode and user permissions
  const displayedOrganizations = user?.is_superadmin 
    ? (viewMode === 'member' 
        ? (allOrganizations || []).filter(org => isUserMember(org.id))
        : (allOrganizations || []))
    : (allOrganizations || []).filter(org => isUserMember(org.id)); // Non-superadmin users only see their organizations

  // Handle mode switching with confirmation
  const handleModeSwitch = (newMode: 'member' | 'all') => {
    // Only superadmins can switch to "all" mode
    if (newMode === 'all' && !user?.is_superadmin) {
      notificationService.showError('Only superadmins can view all organizations');
      return;
    }
    
    if (newMode === 'all' && viewMode === 'member') {
      setShowModeConfirmation(true);
    } else {
      setViewMode(newMode);
      // Reset selection when changing modes
      setSelectedOrg(null);
    }
  };

  const confirmModeSwitch = () => {
    setViewMode('all');
    setShowModeConfirmation(false);
    setSelectedOrg(null);
  };

  useEffect(() => {
    if (hasAccess) {
      fetchOrganizations();
    } else {
      setLoading(false);
    }
  }, [hasAccess]);

  useEffect(() => {
    if (selectedOrg) {
      fetchMembers(selectedOrg.id);
      fetchInvitations(selectedOrg.id);
      // also refresh counts
      try { refreshInvitationCounts(selectedOrg.id); } catch {}
    }
  }, [selectedOrg, invitationFilter]);

  const fetchOrganizations = async () => {
    try {
      // Fetch manageable organizations and user memberships
      const [orgs, userOrgs] = await Promise.all([
        // Use manageable endpoint which handles both regular users and superadmins appropriately
        organizationService.getManageableOrganizations(),
        // Always fetch user's memberships for styling purposes (superadmin safety indicators)
        organizationService.getOrganizations()
      ]);
      
      setAllOrganizations(orgs);
      setUserMemberOrganizations(userOrgs);
      
      if (orgs.length > 0 && !selectedOrg) {
        setSelectedOrg(orgs[0]);
      }
    } catch (error) {
      // Error notifications are now handled by the API service
      console.error('Error fetching organizations:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchMembers = async (orgId: string) => {
    try {
      const orgMembers = await organizationService.getMembers(orgId);
      setMembers(orgMembers);
    } catch (error) {
      notificationService.showError('Failed to fetch organization members');
      console.error('Error fetching members:', error);
    }
  };

  async function fetchInvitations(orgId: string) {
    try {
      if (invitationFilter === 'all') {
        const all = await organizationService.listInvitations(orgId, 'all');
        setInvitations(all || []);
      } else {
        const invs = await organizationService.listInvitations(orgId, invitationFilter);
        setInvitations(invs || []);
      }
    } catch (error) {
      console.error('Error fetching invitations:', error);
      notificationService.showError('Failed to fetch invitations');
    }
  }

  async function refreshInvitationCounts(orgId: string) {
    try {
      const [p, a, r, e] = await Promise.all([
        organizationService.listInvitations(orgId, 'pending'),
        organizationService.listInvitations(orgId, 'accepted'),
        organizationService.listInvitations(orgId, 'revoked'),
        organizationService.listInvitations(orgId, 'expired'),
      ]);
      setInvCounts({ pending: (p||[]).length, accepted: (a||[]).length, revoked: (r||[]).length, expired: (e||[]).length });
    } catch {}
  }

  // Auto-refresh pending invitations at configurable interval
  const getInvitationsRefreshMs = (): number => {
    try {
      // Prefer runtime __ENV__ value if present, else VITE_ from process.env
      const runtime = (typeof window !== 'undefined' && (window as any).__ENV__?.INVITATIONS_REFRESH_MS) || null;
      const build = (typeof process !== 'undefined' && (process as any).env?.VITE_INVITATIONS_REFRESH_MS) || null;
      const val = Number(runtime ?? build);
      return Number.isFinite(val) && val > 0 ? val : 30000; // default 30s
    } catch {
      return 30000;
    }
  };

  useEffect(() => {
    if (!selectedOrg) return;
    const ms = getInvitationsRefreshMs();
    const id = setInterval(() => {
      try { 
        fetchInvitations(selectedOrg.id);
        refreshInvitationCounts(selectedOrg.id);
      } catch {}
    }, ms);
    return () => clearInterval(id);
  }, [selectedOrg, invitationFilter]);

  const handleCreateOrganization = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgData.name.trim()) {
      notificationService.showError('Organization name is required');
      return;
    }

    try {
      const newOrg = await organizationService.createOrganization({
        name: newOrgData.name.trim(),
        slug: newOrgData.slug?.trim() || undefined,
      });
      
      // Refresh user data to update memberships (critical for delete button visibility)
      await refreshUser();
      
      await fetchOrganizations();
      
      // Also refresh the organization dropdown in the context
      try {
        await refreshOrganizations();
      } catch (error) {
        console.error('Failed to refresh organization dropdown after creation:', error);
        // Don't fail the entire operation if dropdown refresh fails
      }
      
      setSelectedOrg(newOrg);
      setCreateMode(false);
      setNewOrgData({ name: '', slug: '' });
      // Success notification is now handled by the API service
    } catch (error) {
      // Error notifications are now handled by the API service
      console.error('Failed to create organization:', error);
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg || !newMemberData.email.trim()) {
      notificationService.showError('Email is required');
      return;
    }

    try {
      // Send an invitation instead of directly adding the member
      await organizationService.createInvitation(selectedOrg.id, {
        email: newMemberData.email.trim(),
        role: newMemberData.role,
      });

      await fetchInvitations(selectedOrg.id);
      setAddMemberMode(false);
      setNewMemberData({ email: '', role: 'viewer' });
      notificationService.showSuccess('Invitation sent');
    } catch (error) {
      notificationService.showError(`Failed to send invitation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleRemoveMember = async (userId: string, email: string) => {
    if (!selectedOrg) return;
    
    if (confirm(`Are you sure you want to remove ${email} from the organization?`)) {
      try {
        await organizationService.removeMember(selectedOrg.id, userId);
        await fetchMembers(selectedOrg.id);
        notificationService.showSuccess('Member removed successfully');
      } catch (error) {
        notificationService.showError(`Failed to remove member: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    if (!selectedOrg) return;

    try {
      await organizationService.updateMember(selectedOrg.id, userId, {
        role: newRole,
      });
      await fetchMembers(selectedOrg.id);
      notificationService.showSuccess('Member role updated successfully');
    } catch (error) {
      notificationService.showError(`Failed to update member role: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleDeleteOrganization = async () => {
    if (!selectedOrg) return;

    try {
      await organizationService.deleteOrganization(selectedOrg.id);
      
      // Refresh the organizations list
      await fetchOrganizations();
      
      // Also refresh the organization dropdown in the context
      try {
        await refreshOrganizations();
      } catch (error) {
        console.error('Failed to refresh organization dropdown after deletion:', error);
      }
      
      // Clear the selected organization
      setSelectedOrg(null);
      setShowDeleteConfirmation(false);
      notificationService.showSuccess('Organization deleted successfully');
    } catch (error) {
      notificationService.showError(`Failed to delete organization: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setShowDeleteConfirmation(false);
    }
  };

  const canManageOrganization = (org: Organization | null): boolean => {
    if (!org || !user) return false;
    if (user.is_superadmin) return true;
    
    // Check if user is a member with admin or owner role using user's memberships
    const membership = user.memberships?.find(m => m.organization_id === org.id);
    return membership ? ['admin', 'owner'].includes(membership.role || '') : false;
  };

  if (loading) {
    return (
      <Portal>
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              <span className="ml-2">Loading organizations...</span>
            </div>
          </div>
        </div>
      </Portal>
    );
  }

  if (!hasAccess) {
    return (
      <Portal>
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gray-800">Access Denied</h2>
              <button
                onClick={handleClose}
                className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
              >
                ×
              </button>
            </div>
            <div className="text-center py-8">
              <p className="text-gray-600">You need to be authenticated to access organization management.</p>
            </div>
          </div>
        </div>
      </Portal>
    );
  }

  return (
    <Portal>
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-6xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800">Organization Management</h2>
          <button
            onClick={handleClose}
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
          >
            ×
          </button>
        </div>

        {/* View Mode Toggle */}
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <span className="font-medium text-gray-700">View Mode:</span>
              <div className="flex bg-white rounded-lg p-1 border">
                <button
                  onClick={() => handleModeSwitch('member')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition ${
                    viewMode === 'member'
                      ? 'bg-green-100 text-green-800 border border-green-300'
                      : 'text-gray-600 hover:text-gray-800'
                  }`}
                >
                  My Organizations
                </button>
                {/* Only superadmins can see "All Organizations" */}
                {user?.is_superadmin && (
                  <button
                    onClick={() => handleModeSwitch('all')}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition ${
                      viewMode === 'all'
                        ? 'bg-orange-100 text-orange-800 border border-orange-300'
                        : 'text-gray-600 hover:text-gray-800'
                    }`}
                  >
                    All Organizations
                  </button>
                )}
              </div>
            </div>
            <div className="text-sm text-gray-500">
              {user?.is_superadmin 
                ? (viewMode === 'member' 
                    ? `Showing ${displayedOrganizations.length} organizations where you are a member`
                    : `Showing ${displayedOrganizations.length} organizations (${userMemberOrganizations.length} member, ${displayedOrganizations.length - userMemberOrganizations.length} admin-only)`)
                : `Showing ${displayedOrganizations.length} organizations where you are a member`
              }
            </div>
            

          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Organizations List */}
          <div className="lg:col-span-1">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Organizations</h3>
              <button
                onClick={() => setCreateMode(true)}
                className="bg-blue-500 text-white px-3 py-1 rounded text-sm hover:bg-blue-600 transition"
              >
                + New
              </button>
            </div>

            {createMode && (
              <form onSubmit={handleCreateOrganization} className="mb-4 p-3 border rounded bg-gray-50">
                <div className="mb-2">
                  <input
                    type="text"
                    placeholder="Organization Name"
                    value={newOrgData.name}
                    onChange={(e) => setNewOrgData({ ...newOrgData, name: e.target.value })}
                    className="w-full px-2 py-1 border rounded text-sm"
                    required
                  />
                </div>
                <div className="mb-2">
                  <input
                    type="text"
                    placeholder="Slug (optional)"
                    value={newOrgData.slug}
                    onChange={(e) => setNewOrgData({ ...newOrgData, slug: e.target.value })}
                    className="w-full px-2 py-1 border rounded text-sm"
                  />
                </div>
                <div className="flex gap-2">
                  <button type="submit" className="bg-green-500 text-white px-2 py-1 rounded text-sm hover:bg-green-600">
                    Create
                  </button>
                  <button
                    type="button"
                    onClick={() => setCreateMode(false)}
                    className="bg-gray-500 text-white px-2 py-1 rounded text-sm hover:bg-gray-600"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}

            <div className="space-y-2">
              {displayedOrganizations.map((org: Organization) => {
                const isMember = isUserMember(org.id);
                const membershipBorderClass = isMember 
                  ? 'border-l-4 border-l-green-500' 
                  : 'border-l-4 border-l-red-500';
                const membershipBgClass = selectedOrg?.id === org.id 
                  ? 'bg-blue-50 border-blue-300' 
                  : isMember 
                    ? 'hover:bg-green-50' 
                    : 'hover:bg-red-50';

                return (
                  <div
                    key={org.id}
                    onClick={async () => {
                      // Non-superadmin users can only select organizations where they are members
                      if (!user?.is_superadmin && !isMember) {
                        notificationService.showError('You can only access organizations where you are a member');
                        return;
                      }
                      
                      // Refresh user data when switching organizations to ensure button state is correct
                      try {
                        await refreshUser();
                      } catch (error) {
                        console.error('Failed to refresh user data when switching organizations:', error);
                        // Don't block organization switching if refresh fails
                      }
                      
                      setSelectedOrg(org);
                    }}
                    className={`p-3 border rounded transition ${membershipBorderClass} ${membershipBgClass} ${
                      (!user?.is_superadmin && !isMember) ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium">{org.name}</div>
                        {org.slug && <div className="text-sm text-gray-500">{org.slug}</div>}
                      </div>
                      <div className={`text-xs px-2 py-1 rounded ${
                        isMember 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {isMember ? 'Member' : 'Not Member'}
                      </div>
                    </div>
                  </div>
                );
              })}
              {displayedOrganizations.length === 0 && !createMode && (
                <div className="text-gray-500 text-center py-4">
                  No organizations found. Create one to get started.
                </div>
              )}
            </div>
          </div>

          {/* Members Management */}
          <div className="lg:col-span-2">
            {selectedOrg ? (
              <>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold">Members of {selectedOrg.name}</h3>
                  {(user?.is_superadmin || isUserMember(selectedOrg.id)) ? (
                    <div className="flex gap-2">
                      <button
                        onClick={() => setAddMemberMode(true)}
                        className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 transition"
                      >
                        + Invite Member
                      </button>
                      <button
                        onClick={() => setInviteMode(true)}
                        className="bg-blue-500 text-white px-3 py-1 rounded text-sm hover:bg-blue-600 transition"
                      >
                        + Invite
                      </button>
                      {canManageOrganization(selectedOrg) && (
                        <button
                          onClick={() => setShowDeleteConfirmation(true)}
                          className="bg-red-500 text-white px-3 py-1 rounded text-sm hover:bg-red-600 transition"
                        >
                          Delete Org
                        </button>
                      )}
                    </div>
                  ) : (
                    <span className="text-sm text-gray-500 italic">Read-only (not a member)</span>
                  )}
                </div>
                


                {addMemberMode && (user?.is_superadmin || isUserMember(selectedOrg.id)) && (
                  <form onSubmit={handleAddMember} className="mb-4 p-4 border rounded bg-gray-50">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                      <input
                        type="email"
                        placeholder="Invitee Email"
                        value={newMemberData.email}
                        onChange={(e) => setNewMemberData({ ...newMemberData, email: e.target.value })}
                        className="px-3 py-2 border rounded"
                        required
                      />
                      <select
                        value={newMemberData.role}
                        onChange={(e) => setNewMemberData({ ...newMemberData, role: e.target.value })}
                        className="px-3 py-2 border rounded"
                      >
                        <option value="viewer">Viewer</option>
                        <option value="editor">Editor</option>
                        <option value="admin">Admin</option>
                        <option value="owner">Owner</option>
                      </select>
                    </div>
                    <div className="flex gap-2">
                      <button type="submit" className="bg-green-600 text-white px-3 py-2 rounded hover:bg-green-700">
                        Send Invitation
                      </button>
                      <button
                        type="button"
                        onClick={() => setAddMemberMode(false)}
                        className="bg-gray-500 text-white px-3 py-2 rounded hover:bg-gray-600"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                )}

                {/* Invitation Create Form */}
                {inviteMode && (user?.is_superadmin || isUserMember(selectedOrg.id)) && (
                  <form
                    onSubmit={async (e) => {
                      e.preventDefault();
                      if (!selectedOrg) return;
                      try {
                        // Prevent duplicate pending invite client-side
                        const dup = invitations.find((i) => (i.email || '').toLowerCase() === inviteEmail.toLowerCase() && (i.status || '').toLowerCase() === 'pending');
                        if (dup) {
                          notificationService.showInfo('A pending invitation already exists for this email');
                          return;
                        }
                        await organizationService.createInvitation(selectedOrg.id, { email: inviteEmail, role: inviteRole });
                        notificationService.showSuccess('Invitation sent');
                        setInviteEmail('');
                        setInviteRole('viewer');
                        setInviteMode(false);
                        await fetchInvitations(selectedOrg.id);
                      } catch (error: any) {
                        notificationService.showError(`Failed to send invitation: ${error?.message || 'Unknown error'}`);
                      }
                    }}
                    className="mb-4 p-4 border rounded bg-blue-50"
                  >
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                      <input
                        type="email"
                        placeholder="Invitee Email"
                        value={inviteEmail}
                        onChange={(e) => setInviteEmail(e.target.value)}
                        className="px-3 py-2 border rounded"
                        required
                      />
                      <select
                        value={inviteRole}
                        onChange={(e) => setInviteRole(e.target.value)}
                        className="px-3 py-2 border rounded"
                      >
                        <option value="viewer">Viewer</option>
                        <option value="editor">Editor</option>
                        <option value="admin">Admin</option>
                        <option value="owner">Owner</option>
                      </select>
                    </div>
                    <div className="flex gap-2">
                      <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded hover:bg-blue-700">
                        Send Invitation
                      </button>
                      <button
                        type="button"
                        onClick={() => setInviteMode(false)}
                        className="bg-gray-500 text-white px-3 py-2 rounded hover:bg-gray-600"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                )}

                <div className="overflow-x-auto">
                  <table className="w-full border-collapse border border-gray-300">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border border-gray-300 px-4 py-2 text-left">Email</th>
                        <th className="border border-gray-300 px-4 py-2 text-left">Display Name</th>
                        <th className="border border-gray-300 px-4 py-2 text-left">Role</th>
                        <th className="border border-gray-300 px-4 py-2 text-left">Permissions</th>
                        <th className="border border-gray-300 px-4 py-2 text-left">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {members.map((member) => (
                        <tr key={member.user_id} className="hover:bg-gray-50">
                          <td className="border border-gray-300 px-4 py-2">{member.email}</td>
                          <td className="border border-gray-300 px-4 py-2">{member.display_name}</td>
                          <td className="border border-gray-300 px-4 py-2">
                            <select
                              value={member.role}
                              onChange={(e) => handleRoleChange(member.user_id, e.target.value)}
                              className="px-2 py-1 border rounded text-sm"
                              disabled={member.email === user?.email} // Prevent self-modification
                            >
                              <option value="viewer">Viewer</option>
                              <option value="editor">Editor</option>
                              <option value="admin">Admin</option>
                              <option value="owner">Owner</option>
                            </select>
                          </td>
                          <td className="border border-gray-300 px-4 py-2 text-sm">
                            <span className={`inline-block px-2 py-1 rounded text-xs mr-1 ${member.can_read ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                              {member.can_read ? 'Read' : 'No Read'}
                            </span>
                            <span className={`inline-block px-2 py-1 rounded text-xs ${member.can_write ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                              {member.can_write ? 'Write' : 'No Write'}
                            </span>
                          </td>
                          <td className="border border-gray-300 px-4 py-2">
                            {member.email !== user?.email && (
                              <button
                                onClick={() => handleRemoveMember(member.user_id, member.email)}
                                className="bg-red-500 text-white px-2 py-1 rounded text-sm hover:bg-red-600 transition"
                              >
                                Remove
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {members.length === 0 && (
                    <div className="text-gray-500 text-center py-8">
                      No members found. Add some members to get started.
                    </div>
                  )}
                </div>

                {/* Invitations Section */}
                <div className="mt-8">
                  <div className="flex flex-col gap-2 mb-3">
                    <div className="flex justify-between items-center">
                      <h3 className="text-lg font-semibold">Invitations</h3>
                      <div className="text-xs text-gray-600 bg-gray-100 rounded-full px-3 py-1">
                        Pending: <span className="text-amber-700 font-semibold">{invCounts.pending}</span> • Accepted: <span className="text-green-700 font-semibold">{invCounts.accepted}</span> • Revoked: <span className="text-red-700 font-semibold">{invCounts.revoked}</span> • Expired: <span className="text-gray-700 font-semibold">{invCounts.expired}</span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {(['pending','accepted','revoked','expired','all'] as const).map(s => (
                        <button key={s} onClick={() => setInvitationFilter(s)} className={`px-3 py-1 rounded text-sm border ${invitationFilter===s? 'bg-blue-600 text-white border-blue-600':'bg-white text-gray-700 hover:bg-gray-50'}`}>{s.charAt(0).toUpperCase()+s.slice(1)}</button>
                      ))}
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse border border-gray-300">
                      <thead>
                        <tr className="bg-gray-100">
                          <th className="border px-3 py-2 text-left">Email</th>
                          <th className="border px-3 py-2 text-left">Role</th>
                          <th className="border px-3 py-2 text-left">Status</th>
                          <th className="border px-3 py-2 text-left">Created</th>
                          <th className="border px-3 py-2 text-left">Expires</th>
                          <th className="border px-3 py-2 text-left">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {invitations.map((inv) => {
                          const isPending = (inv.status || '').toLowerCase() === 'pending';
                          return (
                            <tr key={inv.id} className="hover:bg-gray-50">
                              <td className="border px-3 py-2">{inv.email}</td>
                              <td className="border px-3 py-2">{inv.role}</td>
                              <td className="border px-3 py-2">{inv.status}</td>
                              <td className="border px-3 py-2 text-sm">{new Date(inv.created_at).toLocaleString()}</td>
                              <td className="border px-3 py-2 text-sm">{new Date(inv.expires_at).toLocaleString()}</td>
                              <td className="border px-3 py-2">
                                <div className="flex gap-2">
                                  <button
                                    disabled={!isPending}
                                    onClick={async () => {
                                      if (!selectedOrg) return;
                                      try {
                                        await organizationService.resendInvitation(selectedOrg.id, inv.id);
                                        notificationService.showSuccess('Invitation resent');
                                        await fetchInvitations(selectedOrg.id);
                                        await refreshInvitationCounts(selectedOrg.id);
                                      } catch (error: any) {
                                        notificationService.showError(`Failed to resend: ${error?.message || 'Unknown error'}`);
                                      }
                                    }}
                                    className={`px-2 py-1 rounded text-sm ${isPending ? 'bg-amber-500 hover:bg-amber-600 text-white' : 'bg-gray-300 text-gray-600 cursor-not-allowed'}`}
                                  >
                                    Resend
                                  </button>
                                  <button
                                    onClick={async () => {
                                      if (!selectedOrg) return;
                                      try {
                                        await organizationService.revokeInvitation(selectedOrg.id, inv.id);
                                        notificationService.showInfo('Invitation revoked');
                                        await fetchInvitations(selectedOrg.id);
                                        await refreshInvitationCounts(selectedOrg.id);
                                      } catch (error: any) {
                                        notificationService.showError(`Failed to revoke: ${error?.message || 'Unknown error'}`);
                                      }
                                    }}
                                    className="px-2 py-1 rounded text-sm bg-red-500 hover:bg-red-600 text-white"
                                  >
                                    Revoke
                                  </button>
                                  <button
                                    onClick={() => setAuditOpen({open:true, invitationId: inv.id})}
                                    className="px-2 py-1 rounded text-sm bg-gray-200 hover:bg-gray-300 text-gray-800"
                                  >
                                    View Audit
                                  </button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                        {invitations.length === 0 && (
                          <tr><td colSpan={6} className="border px-3 py-6 text-center text-gray-500">No invitations found.</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                  {auditOpen.open && (
                    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-60" onClick={() => setAuditOpen({open:false})}>
                      <div className="bg-white rounded-lg p-4 w-full max-w-2xl mx-4" onClick={(e)=>e.stopPropagation()}>
                        <div className="flex justify-between items-center mb-3">
                          <h4 className="text-md font-semibold">Invitation Audit</h4>
                          <button onClick={() => setAuditOpen({open:false})} className="text-gray-500 hover:text-gray-700">×</button>
                        </div>
                        <AuditLogs invitationId={auditOpen.invitationId!} orgId={selectedOrg!.id} />
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="text-gray-500 text-center py-8">
                Select an organization to manage its members.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mode Switch Confirmation Dialog */}
      {showModeConfirmation && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-60">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center mb-4">
              <div className="flex-shrink-0 w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                <span className="text-orange-600 font-bold">!</span>
              </div>
              <div className="ml-3">
                <h3 className="text-lg font-medium text-gray-900">Switch to All Organizations?</h3>
              </div>
            </div>
            <div className="mb-4">
              <p className="text-sm text-gray-500">
                You are about to view all organizations, including those where you are not a member. 
                Organizations where you are not a member will be clearly marked and you should exercise 
                caution when managing them.
              </p>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowModeConfirmation(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={confirmModeSwitch}
                className="px-4 py-2 text-sm font-medium text-white bg-orange-600 rounded-md hover:bg-orange-700"
              >
                Show All Organizations
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Organization Confirmation Dialog */}
      {showDeleteConfirmation && selectedOrg && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-60">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center mb-4">
              <div className="flex-shrink-0 w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <span className="text-red-600 font-bold">⚠</span>
              </div>
              <div className="ml-3">
                <h3 className="text-lg font-medium text-gray-900">Delete Organization</h3>
              </div>
            </div>
            <div className="mb-4">
              <p className="text-sm text-gray-500">
                Are you sure you want to delete the organization "{selectedOrg.name}"? 
                This action cannot be undone. Make sure all agents, memories, and keywords 
                have been removed from the organization first.
              </p>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowDeleteConfirmation(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteOrganization}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
              >
                Delete Organization
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
    </Portal>
  );
};

export default OrganizationManagement;

// Lightweight audit log viewer component
const AuditLogs: React.FC<{invitationId: string; orgId: string}> = ({ invitationId, orgId }) => {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true); setError(null);
        const res = await apiFetch(`/audits`, { searchParams: { organization_id: orgId, limit: 200 } });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const filtered = (data || []).filter((l: any) => (l?.target_type || '').toLowerCase() === 'invitation' && String(l?.target_id || '').toLowerCase() === invitationId.toLowerCase());
        setLogs(filtered);
      } catch (e: any) {
        setError(e?.message || 'Failed to load');
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [invitationId, orgId]);

  if (loading) return <div className="text-sm text-gray-600">Loading audit logs…</div>;
  if (error) return <div className="text-sm text-red-600">{error}</div>;
  if (!logs.length) return <div className="text-sm text-gray-600">No audit events for this invitation.</div>;

  return (
    <div className="max-h-80 overflow-y-auto">
      <table className="w-full border-collapse border border-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="border px-2 py-1 text-left">Time</th>
            <th className="border px-2 py-1 text-left">Action</th>
            <th className="border px-2 py-1 text-left">Status</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((l:any) => (
            <tr key={l.id}>
              <td className="border px-2 py-1">{new Date(l.created_at).toLocaleString()}</td>
              <td className="border px-2 py-1">{l.action_type}</td>
              <td className="border px-2 py-1">{l.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
