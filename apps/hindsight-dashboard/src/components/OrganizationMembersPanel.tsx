import React, { useState } from 'react';
import { Organization, OrganizationMember, OrganizationInvitation, AddMemberData } from '../api/organizationService';
import organizationService from '../api/organizationService';
import notificationService from '../services/notificationService';
import OrganizationInvitationsPanel from './OrganizationInvitationsPanel';

interface OrganizationMembersPanelProps {
  selectedOrg: Organization;
  members: OrganizationMember[];
  invitations: OrganizationInvitation[];
  invitationFilter: 'pending' | 'accepted' | 'revoked' | 'expired' | 'all';
  invCounts: { pending: number; accepted: number; revoked: number; expired: number };
  currentUserEmail: string | undefined;
  canManage: boolean;
  isMember: boolean;
  onRefreshMembers: () => Promise<void>;
  onRefreshInvitations: () => Promise<void>;
  onRefreshCounts: () => Promise<void>;
  onFilterChange: (filter: 'pending' | 'accepted' | 'revoked' | 'expired' | 'all') => void;
  onDeleteOrgClick: () => void;
}

const OrganizationMembersPanel: React.FC<OrganizationMembersPanelProps> = ({
  selectedOrg,
  members,
  invitations,
  invitationFilter,
  invCounts,
  currentUserEmail,
  canManage,
  isMember,
  onRefreshMembers,
  onRefreshInvitations,
  onRefreshCounts,
  onFilterChange,
  onDeleteOrgClick,
}) => {
  const [addMemberMode, setAddMemberMode] = useState(false);
  const [newMemberData, setNewMemberData] = useState<AddMemberData>({ email: '', role: 'viewer' });

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemberData.email.trim()) {
      notificationService.showError('Email is required');
      return;
    }

    try {
      // Send an invitation instead of directly adding the member
      await organizationService.createInvitation(selectedOrg.id, {
        email: newMemberData.email.trim(),
        role: newMemberData.role,
      });

      await onRefreshInvitations();
      setAddMemberMode(false);
      setNewMemberData({ email: '', role: 'viewer' });
      notificationService.showSuccess('Invitation sent');
    } catch (error) {
      notificationService.showError(`Failed to send invitation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleRemoveMember = async (userId: string, email: string) => {
    if (confirm(`Are you sure you want to remove ${email} from the organization?`)) {
      try {
        await organizationService.removeMember(selectedOrg.id, userId);
        await onRefreshMembers();
        notificationService.showSuccess('Member removed successfully');
      } catch (error) {
        notificationService.showError(`Failed to remove member: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await organizationService.updateMember(selectedOrg.id, userId, {
        role: newRole,
      });
      await onRefreshMembers();
      notificationService.showSuccess('Member role updated successfully');
    } catch (error) {
      notificationService.showError(`Failed to update member role: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  return (
    <>
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-semibold">Members of {selectedOrg.name}</h3>
        {isMember ? (
          <div className="flex gap-2">
            <button
              onClick={() => setAddMemberMode(true)}
              className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 transition"
            >
              + Invite Member
            </button>
            {/* Removed duplicate '+ Invite' button — use '+ Invite Member' which sends an invitation and requires accept/decline by the invitee */}
            {canManage && (
              <button
                onClick={onDeleteOrgClick}
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
      <div className="text-xs text-gray-500 mb-3 flex items-center gap-2">
        <span>Org ID: {selectedOrg.id}</span>
        <button
          onClick={() => { navigator.clipboard.writeText(selectedOrg.id); notificationService.showSuccess('Organization ID copied'); }}
          className="px-2 py-0.5 border rounded hover:bg-gray-100"
          title="Copy Organization ID"
        >
          Copy
        </button>
      </div>

      {addMemberMode && isMember && (
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

      {/* Invitation creation is handled via the '+ Invite Member' quick form which sends invitations. The Invitations section below remains for listing, resending, revoking, and accepting invites. */}

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
                    disabled={member.email === currentUserEmail} // Prevent self-modification
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
                  {member.email !== currentUserEmail && (
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
      <OrganizationInvitationsPanel
        selectedOrg={selectedOrg}
        invitations={invitations}
        invitationFilter={invitationFilter}
        invCounts={invCounts}
        onFilterChange={onFilterChange}
        onRefreshInvitations={onRefreshInvitations}
        onRefreshCounts={onRefreshCounts}
      />
    </>
  );
};

export default OrganizationMembersPanel;
