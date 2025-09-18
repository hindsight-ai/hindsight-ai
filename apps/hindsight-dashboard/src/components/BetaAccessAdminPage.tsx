import React, { useEffect, useMemo, useState } from 'react';
import betaAccessAdminService, { BetaAccessAdminUser, BetaAccessManualStatus } from '../api/betaAccessAdminService';
import notificationService from '../services/notificationService';

const STATUS_OPTIONS: BetaAccessManualStatus[] = ['accepted', 'denied', 'revoked', 'not_requested'];

const statusLabel: Record<BetaAccessManualStatus, string> = {
  accepted: 'Accepted',
  denied: 'Denied',
  revoked: 'Revoked',
  not_requested: 'Not Requested',
};

const BetaAccessAdminPage: React.FC = () => {
  const [users, setUsers] = useState<BetaAccessAdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await betaAccessAdminService.fetchUsers();
      setUsers(data);
    } catch (err: any) {
      const message = err?.message ?? 'Unable to load beta access users.';
      setError(message);
      notificationService.showError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadUsers();
  }, []);

  const handleStatusChange = async (userId: string, newStatus: BetaAccessManualStatus) => {
    setUpdating(userId);
    try {
      const updated = await betaAccessAdminService.updateStatus(userId, newStatus);
      setUsers(prev => prev.map(u => (u.user_id === userId ? updated : u)));
      notificationService.showSuccess(`Updated beta access status to ${statusLabel[newStatus]}`);
    } catch (err: any) {
      const message = err?.message ?? 'Unable to update status.';
      notificationService.showError(message);
    } finally {
      setUpdating(null);
    }
  };

  const rows = useMemo(() => {
    return users.map((user) => {
      const request = user.last_request;
      return (
        <tr key={user.user_id} className="border-b last:border-0">
          <td className="px-4 py-3 align-top">
            <div className="font-medium text-gray-900">{user.display_name || '—'}</div>
            <div className="text-sm text-gray-500">{user.email}</div>
          </td>
          <td className="px-4 py-3 align-top">
            <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-medium uppercase tracking-wide text-slate-700">
              {user.beta_access_status}
            </span>
          </td>
          <td className="px-4 py-3 align-top text-sm text-gray-700">
            {request ? (
              <div className="space-y-1">
                <div><span className="font-medium">Status:</span> {request.status}</div>
                <div><span className="font-medium">Requested:</span> {request.requested_at || '—'}</div>
                <div><span className="font-medium">Reviewed:</span> {request.reviewed_at || '—'}</div>
                {request.reviewer_email ? (
                  <div><span className="font-medium">Reviewer:</span> {request.reviewer_email}</div>
                ) : null}
              </div>
            ) : (
              <span className="text-gray-400">No request on record</span>
            )}
          </td>
          <td className="px-4 py-3 align-top">
            <select
              className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
              value={user.beta_access_status}
              onChange={(event) => handleStatusChange(user.user_id, event.target.value as BetaAccessManualStatus)}
              disabled={updating === user.user_id}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {statusLabel[option]}
                </option>
              ))}
            </select>
          </td>
        </tr>
      );
    });
  }, [users, updating]);

  return (
    <div className="min-h-screen bg-slate-50 py-10">
      <div className="mx-auto max-w-6xl px-4">
        <h1 className="text-2xl font-semibold text-slate-900">Beta Access Administrator Console</h1>
        <p className="mt-1 text-sm text-slate-600">
          Manage beta access manually for staging or support scenarios. Changes are audited automatically.
        </p>

        {loading ? (
          <div className="mt-8 rounded-lg border border-slate-200 bg-white p-6 text-slate-600">Loading users…</div>
        ) : error ? (
          <div className="mt-8 rounded-lg border border-rose-200 bg-rose-50 p-6 text-rose-700">{error}</div>
        ) : (
          <div className="mt-8 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-100 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                <tr>
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">Current Status</th>
                  <th className="px-4 py-3">Latest Request</th>
                  <th className="px-4 py-3">Set Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm text-slate-700">{rows}</tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default BetaAccessAdminPage;
