import React, { useEffect, useState } from 'react';
import organizationService, { Organization } from '../api/organizationService';
import useTokenCreation from '../hooks/useTokenCreation';
import notificationService from '../services/notificationService';
import { CopyToClipboardButton } from './CopyToClipboardButton';

interface Props { isOpen: boolean; onClose: () => void }

const QuickCreateTokenModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const { create, loading, oneTimeSecret, clearOneTime } = useTokenCreation();
  const [name, setName] = useState('Quick token');
  const [scopes, setScopes] = useState<{ read: boolean; write: boolean }>({ read: true, write: false });
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [organizationId, setOrganizationId] = useState<string>('');
  // oneTimeSecret comes from hook

  useEffect(() => {
    if (!isOpen) return;
    let mounted = true;
    (async () => {
      try {
        const list = await organizationService.getOrganizations().catch(() => [] as Organization[]);
        if (mounted) setOrgs(list);
      } catch (e) {
        // ignore
      }
    })();
    return () => { mounted = false; };
  }, [isOpen]);

  const reset = () => {
    setName('Quick token');
    setScopes({ read: true, write: false });
    setOrganizationId('');
    clearOneTime();
  };

  const closeAndReset = () => { reset(); onClose(); };

  const onCreate = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!name.trim()) return notificationService.showWarning('Token name is required');
    const chosen = Object.entries(scopes).filter(([k, v]) => v).map(([k]) => k);
    if (chosen.length === 0) return notificationService.showWarning('Select at least one scope');
    try {
      const payload: any = { name: name.trim(), scopes: chosen };
      if (organizationId) payload.organization_id = organizationId;
      await create(payload);
    } catch (err) {
      // hook already shows notifications
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black opacity-40" onClick={closeAndReset}></div>
      <div className="bg-white rounded shadow-lg max-w-lg w-full z-60 p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-lg font-semibold">Quick create API token</h3>
          <button className="text-gray-500" onClick={closeAndReset} aria-label="Close">✕</button>
        </div>
        <form onSubmit={onCreate} className="mt-3">
          <label className="block text-sm text-gray-600 mb-1">Name</label>
          <input className="w-full px-3 py-2 border rounded" value={name} onChange={e => setName(e.target.value)} />

          <div className="mt-3 flex items-center gap-4">
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={scopes.read} onChange={e => setScopes(s => ({ ...s, read: e.target.checked }))} /> read
            </label>
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={scopes.write} onChange={e => setScopes(s => ({ ...s, write: e.target.checked }))} /> write
            </label>
          </div>

          <div className="mt-3">
            <label className="block text-sm text-gray-600 mb-1">Organization (optional)</label>
            <select className="w-full px-3 py-2 border rounded" value={organizationId} onChange={e => setOrganizationId(e.target.value)}>
              <option value="">— None —</option>
              {orgs.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
          </div>

          {oneTimeSecret ? (
            <div className="mt-4 p-3 border rounded bg-yellow-50 text-yellow-800">
              <div className="mb-2">Copy and store the token now — it will not be shown again.</div>
              <div className="flex items-center gap-2">
                <code className="text-xs break-all">{oneTimeSecret}</code>
                <CopyToClipboardButton textToCopy={oneTimeSecret} displayId="QuickCopy" />
                <button type="button" className="ml-auto text-sm text-blue-600 hover:underline" onClick={() => { clearOneTime(); closeAndReset(); }}>Done</button>
              </div>
            </div>
          ) : (
            <div className="mt-4 flex items-center gap-2">
              <button type="submit" disabled={loading} className="px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">Create</button>
              <button type="button" onClick={closeAndReset} className="px-3 py-2 rounded border">Cancel</button>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default QuickCreateTokenModal;
