import React, { useState } from 'react';
import { Organization, OrganizationInvitation } from '../api/organizationService';
import organizationService from '../api/organizationService';
import notificationService from '../services/notificationService';
import AuditLogs from './AuditLogs';

interface OrganizationInvitationsPanelProps {
  selectedOrg: Organization;
  invitations: OrganizationInvitation[];
  invitationFilter: 'pending' | 'accepted' | 'revoked' | 'expired' | 'all';
  invCounts: { pending: number; accepted: number; revoked: number; expired: number };
  onFilterChange: (filter: 'pending' | 'accepted' | 'revoked' | 'expired' | 'all') => void;
  onRefreshInvitations: () => Promise<void>;
  onRefreshCounts: () => Promise<void>;
}

const OrganizationInvitationsPanel: React.FC<OrganizationInvitationsPanelProps> = ({
  selectedOrg,
  invitations,
  invitationFilter,
  invCounts,
  onFilterChange,
  onRefreshInvitations,
  onRefreshCounts,
}) => {
  const [auditOpen, setAuditOpen] = useState<{ open: boolean; invitationId?: string }>({ open: false });

  return (
    <div className="mt-8">
      <div className="flex flex-col gap-2 mb-3">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold">Invitations</h3>
          <div className="text-xs text-gray-600 bg-gray-100 rounded-full px-3 py-1">
            Pending: <span className="text-amber-700 font-semibold">{invCounts.pending}</span> • Accepted: <span className="text-green-700 font-semibold">{invCounts.accepted}</span> • Revoked: <span className="text-red-700 font-semibold">{invCounts.revoked}</span> • Expired: <span className="text-gray-700 font-semibold">{invCounts.expired}</span>
          </div>
        </div>
        <div className="flex gap-2">
          {(['pending', 'accepted', 'revoked', 'expired', 'all'] as const).map(s => (
            <button
              key={s}
              onClick={() => onFilterChange(s)}
              className={`px-3 py-1 rounded text-sm border ${invitationFilter === s ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
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
                          try {
                            await organizationService.resendInvitation(selectedOrg.id, inv.id);
                            notificationService.showSuccess('Invitation resent');
                            await onRefreshInvitations();
                            await onRefreshCounts();
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
                          try {
                            await organizationService.revokeInvitation(selectedOrg.id, inv.id);
                            notificationService.showInfo('Invitation revoked');
                            await onRefreshInvitations();
                            await onRefreshCounts();
                          } catch (error: any) {
                            notificationService.showError(`Failed to revoke: ${error?.message || 'Unknown error'}`);
                          }
                        }}
                        className="px-2 py-1 rounded text-sm bg-red-500 hover:bg-red-600 text-white"
                      >
                        Revoke
                      </button>
                      <button
                        onClick={() => setAuditOpen({ open: true, invitationId: inv.id })}
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
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-60" onClick={() => setAuditOpen({ open: false })}>
          <div className="bg-white rounded-lg p-4 w-full max-w-2xl mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-3">
              <h4 className="text-md font-semibold">Invitation Audit</h4>
              <button onClick={() => setAuditOpen({ open: false })} className="text-gray-500 hover:text-gray-700">×</button>
            </div>
            <AuditLogs invitationId={auditOpen.invitationId!} orgId={selectedOrg.id} />
          </div>
        </div>
      )}
    </div>
  );
};

export default OrganizationInvitationsPanel;
