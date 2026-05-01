import React, { useState, useEffect } from 'react';
import Portal from './Portal';
import { useAuth } from '../context/AuthContext';
import { useOrganization } from '../context/OrganizationContext';
import organizationService, { Organization, OrganizationMember, CreateOrganizationData, OrganizationInvitation } from '../api/organizationService';
import notificationService from '../services/notificationService';
import OrganizationEditPanel from './OrganizationEditPanel';
import OrganizationMembersPanel from './OrganizationMembersPanel';
import ConfirmationDialog from './ConfirmationDialog';

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
  const [invitationFilter, setInvitationFilter] = useState<'pending' | 'accepted' | 'revoked' | 'expired' | 'all'>('pending');
  const [invCounts, setInvCounts] = useState<{ pending: number; accepted: number; revoked: number; expired: number }>({ pending: 0, accepted: 0, revoked: 0, expired: 0 });
  const [loading, setLoading] = useState(true);
  const [createMode, setCreateMode] = useState(false);
  const [showModeConfirmation, setShowModeConfirmation] = useState(false);
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);

  // hasAccess: true for any authenticated user (superadmin or regular)
  const hasAccess = user?.authenticated === true;

  // Check if user is a member of an organization
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

  const fetchInvitations = async (orgId: string) => {
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
  };

  const refreshInvitationCounts = async (orgId: string) => {
    try {
      const [p, a, r, e] = await Promise.all([
        organizationService.listInvitations(orgId, 'pending'),
        organizationService.listInvitations(orgId, 'accepted'),
        organizationService.listInvitations(orgId, 'revoked'),
        organizationService.listInvitations(orgId, 'expired'),
      ]);
      setInvCounts({ pending: (p || []).length, accepted: (a || []).length, revoked: (r || []).length, expired: (e || []).length });
    } catch {}
  };

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

  const handleCreateOrganization = async (data: CreateOrganizationData) => {
    if (!data.name.trim()) {
      notificationService.showError('Organization name is required');
      return;
    }

    try {
      const newOrg = await organizationService.createOrganization({
        name: data.name.trim(),
        slug: data.slug?.trim() || undefined,
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
      // Success notification is now handled by the API service
    } catch (error) {
      // Error notifications are now handled by the API service
      console.error('Failed to create organization:', error);
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
    const membership = user.memberships?.find((m: any) => m.organization_id === org.id);
    return membership ? ['admin', 'owner'].includes(membership.role || '') : false;
  };

  if (loading) {
    return (
      <Portal>
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto overscroll-contain">
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
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto overscroll-contain">
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
      <div className="bg-white rounded-lg p-6 max-w-6xl w-full mx-4 max-h-[90vh] overflow-y-auto overscroll-contain">
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
              <OrganizationEditPanel
                onSubmit={handleCreateOrganization}
                onCancel={() => setCreateMode(false)}
              />
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
                        <div className="text-[10px] text-gray-400 flex items-center gap-2 mt-0.5">
                          <span>{org.id}</span>
                          <button
                            onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(org.id); notificationService.showSuccess('Organization ID copied'); }}
                            className="px-1 py-0.5 border rounded hover:bg-gray-100"
                            title="Copy Organization ID"
                          >
                            Copy
                          </button>
                        </div>
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
              <OrganizationMembersPanel
                selectedOrg={selectedOrg}
                members={members}
                invitations={invitations}
                invitationFilter={invitationFilter}
                invCounts={invCounts}
                currentUserEmail={user?.email}
                canManage={canManageOrganization(selectedOrg)}
                isMember={user?.is_superadmin || isUserMember(selectedOrg.id)}
                onRefreshMembers={() => fetchMembers(selectedOrg.id)}
                onRefreshInvitations={() => fetchInvitations(selectedOrg.id)}
                onRefreshCounts={() => refreshInvitationCounts(selectedOrg.id)}
                onFilterChange={setInvitationFilter}
                onDeleteOrgClick={() => setShowDeleteConfirmation(true)}
              />
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
        <ConfirmationDialog
          title="Switch to All Organizations?"
          body="You are about to view all organizations, including those where you are not a member. Organizations where you are not a member will be clearly marked and you should exercise caution when managing them."
          confirmLabel="Show All Organizations"
          confirmClassName="px-4 py-2 text-sm font-medium text-white bg-orange-600 rounded-md hover:bg-orange-700"
          iconContent={<span className="text-orange-600 font-bold">!</span>}
          iconBgClass="bg-orange-100"
          onConfirm={confirmModeSwitch}
          onCancel={() => setShowModeConfirmation(false)}
        />
      )}

      {/* Delete Organization Confirmation Dialog */}
      {showDeleteConfirmation && selectedOrg && (
        <ConfirmationDialog
          title="Delete Organization"
          body={`Are you sure you want to delete the organization "${selectedOrg.name}"? This action cannot be undone. Make sure all agents, memories, and keywords have been removed from the organization first.`}
          confirmLabel="Delete Organization"
          confirmClassName="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
          iconContent={<span className="text-red-600 font-bold">⚠</span>}
          iconBgClass="bg-red-100"
          onConfirm={handleDeleteOrganization}
          onCancel={() => setShowDeleteConfirmation(false)}
        />
      )}
    </div>
    </Portal>
  );
};

export default OrganizationManagement;
