import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api/http';
import TokenManagement from './TokenManagement';

const ProfilePage: React.FC = () => {
  const { user, refresh } = useAuth();
  const [displayName, setDisplayName] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const superadminEnabled = Boolean(user?.is_superadmin);
  const betaAdminEnabled = Boolean(user?.beta_access_admin);
  const betaStatus = (user?.beta_access_status || 'not_requested').replace(/_/g, ' ');

  // ...existing code...

  useEffect(() => {
    setDisplayName(user?.display_name || '');
  }, [user]);

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

  

  return (
    <div className="p-4 space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Profile</h2>
        <p className="text-sm text-gray-600 mt-1">Review your account privileges and update basic details.</p>
      </div>

      <section className="bg-white border border-gray-200 rounded-lg shadow-sm max-w-2xl">
        <div className="px-4 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Account Privileges</h3>
          <p className="text-sm text-gray-500">Badges indicate elevated access granted by an administrator.</p>
        </div>
        <div className="px-4 py-4 space-y-3">
          <div className="flex flex-wrap gap-2">
            {superadminEnabled && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
                Superadmin access
              </span>
            )}
            {betaAdminEnabled && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-indigo-100 text-indigo-800">
                Beta access admin
              </span>
            )}
            {!superadminEnabled && !betaAdminEnabled && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-600">
                No elevated privileges
              </span>
            )}
          </div>
          <div className="pt-2">
            <p className="text-sm text-gray-600">Beta access status</p>
            <p className="text-sm font-medium text-gray-900 capitalize">{betaStatus}</p>
          </div>
        </div>
      </section>

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

  {/* Tokens moved to a dedicated page at /tokens */}
    </div>
  );
};

export default ProfilePage;
