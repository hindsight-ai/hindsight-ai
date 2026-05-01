import React, { useState, useEffect } from 'react';
import { apiFetch } from '../api/http';

interface AuditLogsProps {
  invitationId: string;
  orgId: string;
}

// Lightweight audit log viewer component
const AuditLogs: React.FC<AuditLogsProps> = ({ invitationId, orgId }) => {
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
    <div className="max-h-80 overflow-y-auto overscroll-contain">
      <table className="w-full border-collapse border border-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="border px-2 py-1 text-left">Time</th>
            <th className="border px-2 py-1 text-left">Action</th>
            <th className="border px-2 py-1 text-left">Status</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((l: any) => (
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

export default AuditLogs;
