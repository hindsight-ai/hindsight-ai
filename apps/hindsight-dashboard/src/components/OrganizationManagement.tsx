import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useOrganization } from '../context/OrganizationContext';
import organizationService, { Organization, OrganizationMember, CreateOrganizationData, AddMemberData } from '../api/organizationService';
import notificationService from '../services/notificationService';

interface OrganizationManagementProps {
  onClose: () => void;
}

const OrganizationManagement: React.FC<OrganizationManagementProps> = ({ onClose }) => {
  const { user } = useAuth();
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
  const [viewMode, setViewMode] = useState<'member' | 'all'>('member');
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [createMode, setCreateMode] = useState(false);
  const [newOrgData, setNewOrgData] = useState<CreateOrganizationData>({ name: '', slug: '' });
  const [addMemberMode, setAddMemberMode] = useState(false);
  const [newMemberData, setNewMemberData] = useState<AddMemberData>({ email: '', role: 'viewer' });
  const [showModeConfirmation, setShowModeConfirmation] = useState(false);

  // Check if user has access to organization management
  const hasAccess = user?.is_superadmin === true;

  // Check if user is a member of an organization
  const isUserMember = (orgId: string): boolean => {
    return userMemberOrganizations.some(org => org.id === orgId);
  };

  // Get organizations to display based on current view mode
  const displayedOrganizations = viewMode === 'member' 
    ? (allOrganizations || []).filter(org => isUserMember(org.id))
    : (allOrganizations || []);

  // Handle mode switching with confirmation
  const handleModeSwitch = (newMode: 'member' | 'all') => {
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
    }
  }, [selectedOrg]);

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
      notificationService.showError('Failed to fetch organizations');
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
      notificationService.showSuccess(`Organization "${newOrg.name}" created successfully`);
    } catch (error) {
      notificationService.showError(`Failed to create organization: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg || !newMemberData.email.trim()) {
      notificationService.showError('Email is required');
      return;
    }

    try {
      await organizationService.addMember(selectedOrg.id, {
        email: newMemberData.email.trim(),
        role: newMemberData.role,
        can_read: true,
        can_write: newMemberData.role !== 'viewer',
      });
      
      await fetchMembers(selectedOrg.id);
      setAddMemberMode(false);
      setNewMemberData({ email: '', role: 'viewer' });
      notificationService.showSuccess('Member added successfully');
    } catch (error) {
      notificationService.showError(`Failed to add member: ${error instanceof Error ? error.message : 'Unknown error'}`);
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
        can_read: true,
        can_write: newRole !== 'viewer',
      });
      await fetchMembers(selectedOrg.id);
      notificationService.showSuccess('Member role updated successfully');
    } catch (error) {
      notificationService.showError(`Failed to update member role: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-2">Loading organizations...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!hasAccess) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
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
            <p className="text-gray-600">You need superadmin privileges to access organization management.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
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
              </div>
            </div>
            <div className="text-sm text-gray-500">
              {viewMode === 'member' 
                ? `Showing ${displayedOrganizations.length} organizations where you are a member`
                : `Showing ${displayedOrganizations.length} organizations (${userMemberOrganizations.length} member, ${displayedOrganizations.length - userMemberOrganizations.length} admin-only)`
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
                    onClick={() => setSelectedOrg(org)}
                    className={`p-3 border rounded cursor-pointer transition ${membershipBorderClass} ${membershipBgClass}`}
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
                  <button
                    onClick={() => setAddMemberMode(true)}
                    className="bg-green-500 text-white px-3 py-1 rounded text-sm hover:bg-green-600 transition"
                  >
                    + Add Member
                  </button>
                </div>

                {addMemberMode && (
                  <form onSubmit={handleAddMember} className="mb-4 p-4 border rounded bg-gray-50">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                      <input
                        type="email"
                        placeholder="Member Email"
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
                      <button type="submit" className="bg-green-500 text-white px-3 py-2 rounded hover:bg-green-600">
                        Add Member
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
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
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
    </div>
  );
};

export default OrganizationManagement;
