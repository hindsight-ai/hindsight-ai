import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import tokenService, { Token } from '../api/tokenService';
import organizationService, { Organization } from '../api/organizationService';
import notificationService from '../services/notificationService';
import { CopyToClipboardButton } from './CopyToClipboardButton';
import { apiFetch } from '../api/http';

const ProfilePage: React.FC = () => {
  const { user, refresh } = useAuth();
  const [displayName, setDisplayName] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // Tokens state
  const [loadingTokens, setLoadingTokens] = useState(false);
  const [tokens, setTokens] = useState<Token[]>([]);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [createForm, setCreateForm] = useState<{ name: string; scopes: Record<string, boolean>; organization_id?: string; expires_at?: string }>({ name: '', scopes: { read: true, write: false }, organization_id: '', expires_at: '' });
  const [oneTimeSecret, setOneTimeSecret] = useState<string | null>(null);
  const [oneTimeLabel, setOneTimeLabel] = useState<string>('');

  useEffect(() => {
    setDisplayName(user?.display_name || '');
  }, [user]);

  useEffect(() => {
    const init = async () => {
      setLoadingTokens(true);
      try {
        const [toks, organizations] = await Promise.all([
          tokenService.list(),
          organizationService.getOrganizations().catch(() => [] as Organization[]),
        ]);
        setTokens(toks);
        setOrgs(organizations);
      } catch (e: any) {
        console.error('Failed fetching tokens', e);
        notificationService.showError('Failed to load API tokens');
      } finally {
        setLoadingTokens(false);
      }
    };
    void init();
  }, []);

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const resp = await apiFetch('/users/me', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ display_name: displayName }),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`HTTP ${resp.status}: ${text}`);
      }
      await refresh();
      setMessage('Profile updated');
    } catch (err: any) {
      setMessage(`Failed to update: ${err?.message || 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  const orgOptions = useMemo(() => orgs.map(o => ({ id: o.id, name: o.name })), [orgs]);

  const onCreateToken = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const scopes = Object.entries(createForm.scopes).filter(([k, v]) => v).map(([k]) => k);
      if (!createForm.name.trim()) {
        notificationService.showWarning('Token name is required');
        return;
      }
      if (scopes.length === 0) {
        notificationService.showWarning('Select at least one scope');
        return;
      }
      const payload: any = { name: createForm.name.trim(), scopes };
      if (createForm.organization_id) payload.organization_id = createForm.organization_id;
      if (createForm.expires_at) payload.expires_at = createForm.expires_at;
      const created = await tokenService.create(payload);
      setTokens(prev => [created, ...prev]);
      setOneTimeSecret(created.token);
      setOneTimeLabel(`Token “${created.name}” created. Copy and store it now – it won't be shown again.`);
      setCreateForm({ name: '', scopes: { read: true, write: false }, organization_id: '', expires_at: '' });
      notificationService.showSuccess('API token created');
    } catch (e: any) {
      notificationService.showApiError?.(parseInt(e.message?.match(/HTTP (\d+)/)?.[1] || '500', 10), e.message, 'create token');
      notificationService.showError('Failed to create token');
    }
  };

  const onRevoke = async (id: string) => {
    try {
      await tokenService.revoke(id);
      setTokens(prev => prev.map(t => (t.id === id ? { ...t, status: 'revoked' } : t)));
      notificationService.showSuccess('Token revoked');
    } catch (e: any) {
      notificationService.showError('Failed to revoke token');
    }
  };

  const onRotate = async (id: string) => {
    try {
      const rotated = await tokenService.rotate(id);
      setTokens(prev => prev.map(t => (t.id === id ? rotated : t)));
      setOneTimeSecret(rotated.token);
      setOneTimeLabel(`Token “${rotated.name}” rotated. Copy the new secret now.`);
      notificationService.showSuccess('Token rotated');
    } catch (e: any) {
      notificationService.showError('Failed to rotate token');
    }
  };

  const formatDateTime = (iso?: string | null) => (iso ? new Date(iso).toLocaleString() : '—');

  return (
    <div className="p-4">
      <h2 className="text-2xl font-semibold mb-4">Your Profile</h2>
      <form onSubmit={onSave} className="max-w-md space-y-4">
        <div>
          <label className="block text-sm text-gray-600 mb-1">Email</label>
          <input className="w-full px-3 py-2 border rounded bg-gray-100" value={user?.email || ''} disabled />
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">Display Name</label>
          <input
            className="w-full px-3 py-2 border rounded"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            maxLength={80}
            placeholder="Your name"
          />
          <p className="text-xs text-gray-500 mt-1">1–80 characters.</p>
        </div>
        <button
          type="submit"
          disabled={saving}
          className={`px-4 py-2 rounded text-white ${saving ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700'}`}
        >
          {saving ? 'Saving…' : 'Save Changes'}
        </button>
        {message && <div className="text-sm text-gray-700 mt-2">{message}</div>}
      </form>

      <div className="mt-10">
        <h3 className="text-xl font-semibold mb-2">API Tokens</h3>
        <p className="text-sm text-gray-600 mb-4">Create and manage Personal Access Tokens for CLI/MCP usage.</p>

        {oneTimeSecret && (
          <div className="mb-4 p-3 border rounded bg-yellow-50 text-yellow-800">
            <div className="mb-2">{oneTimeLabel}</div>
            <div className="flex items-center gap-2">
              <code className="text-xs break-all">{oneTimeSecret}</code>
              <CopyToClipboardButton textToCopy={oneTimeSecret} displayId="Copy" />
              <button className="ml-auto text-sm text-blue-600 hover:underline" onClick={() => setOneTimeSecret(null)}>Dismiss</button>
            </div>
          </div>
        )}

        <form onSubmit={onCreateToken} className="mb-6 p-4 border rounded max-w-3xl">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Name</label>
              <input className="w-full px-3 py-2 border rounded" value={createForm.name} onChange={(e) => setCreateForm(f => ({ ...f, name: e.target.value }))} placeholder="e.g. Local CLI" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Organization (optional)</label>
              <select className="w-full px-3 py-2 border rounded" value={createForm.organization_id || ''} onChange={(e) => setCreateForm(f => ({ ...f, organization_id: e.target.value }))}>
                <option value="">— None —</option>
                {orgOptions.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
              </select>
              {createForm.organization_id && (
                <div className="mt-1 text-xs text-gray-500 flex items-center gap-2">
                  <span>Org ID: {createForm.organization_id}</span>
                  <CopyToClipboardButton textToCopy={createForm.organization_id} displayId="CopyOrgId" />
                </div>
              )}
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Expires At (optional)</label>
              <input className="w-full px-3 py-2 border rounded" type="datetime-local" value={createForm.expires_at || ''} onChange={(e) => setCreateForm(f => ({ ...f, expires_at: e.target.value }))} />
            </div>
          </div>
          <div className="mt-3 flex items-center gap-4">
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={createForm.scopes.read} onChange={(e) => setCreateForm(f => ({ ...f, scopes: { ...f.scopes, read: e.target.checked } }))} /> read
            </label>
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={createForm.scopes.write} onChange={(e) => setCreateForm(f => ({ ...f, scopes: { ...f.scopes, write: e.target.checked } }))} /> write
            </label>
            <button type="submit" className="ml-auto px-4 py-2 rounded text-white bg-blue-600 hover:bg-blue-700">Create Token</button>
          </div>
        </form>

        <div className="overflow-x-auto">
          <table className="min-w-full border">
            <thead className="bg-gray-100 text-sm">
              <tr>
                <th className="px-3 py-2 text-left border">Name</th>
                <th className="px-3 py-2 text-left border">Token</th>
                <th className="px-3 py-2 text-left border">Scopes</th>
                <th className="px-3 py-2 text-left border">Org</th>
                <th className="px-3 py-2 text-left border">Status</th>
                <th className="px-3 py-2 text-left border">Created</th>
                <th className="px-3 py-2 text-left border">Last Used</th>
                <th className="px-3 py-2 text-left border">Expires</th>
                <th className="px-3 py-2 text-left border">Actions</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {tokens.map(t => (
                <tr key={t.id} className="border-t">
                  <td className="px-3 py-2 border align-top">
                    <div className="font-medium">{t.name}</div>
                    <div className="text-xs text-gray-500">{t.id}</div>
                  </td>
                  <td className="px-3 py-2 border align-top">
                    <code className="text-xs">{t.prefix ? `${t.prefix}…${t.last_four || '????'}` : '—'}</code>
                  </td>
                  <td className="px-3 py-2 border align-top">{t.scopes.join(', ')}</td>
                  <td className="px-3 py-2 border align-top">{t.organization_id ? (orgOptions.find(o => o.id === t.organization_id)?.name || t.organization_id) : '—'}</td>
                  <td className="px-3 py-2 border align-top">{t.status}</td>
                  <td className="px-3 py-2 border align-top">{formatDateTime(t.created_at)}</td>
                  <td className="px-3 py-2 border align-top">{formatDateTime(t.last_used_at)}</td>
                  <td className="px-3 py-2 border align-top">{formatDateTime(t.expires_at)}</td>
                  <td className="px-3 py-2 border align-top">
                    <div className="flex items-center gap-2">
                      <button className="px-3 py-1 rounded text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50" disabled={t.status !== 'active'} onClick={() => onRotate(t.id)}>Rotate</button>
                      <button className="px-3 py-1 rounded text-white bg-red-600 hover:bg-red-700 disabled:opacity-50" disabled={t.status !== 'active'} onClick={() => onRevoke(t.id)}>Revoke</button>
                    </div>
                  </td>
                </tr>
              ))}
              {tokens.length === 0 && !loadingTokens && (
                <tr><td className="px-3 py-4 text-center text-gray-500" colSpan={9}>No tokens yet</td></tr>
              )}
              {loadingTokens && (
                <tr><td className="px-3 py-4 text-center text-gray-500" colSpan={9}>Loading…</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
