import React, { useState, useEffect } from 'react';
import Portal from './Portal';
import agentService from '../api/agentService';
import { useOrg } from '../context/OrgContext';

interface AddAgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const AddAgentModal: React.FC<AddAgentModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [agentName, setAgentName] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const { activeScope, activeOrgId } = useOrg() as any;
  const [snapshotScope, setSnapshotScope] = useState<'personal' | 'organization' | 'public'>('personal');
  const [snapshotOrgId, setSnapshotOrgId] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setAgentName('');
      setError(null);
      // Snapshot scope at open time
      try {
        setSnapshotScope((activeScope as any) || (sessionStorage.getItem('ACTIVE_SCOPE') as any) || 'personal');
        setSnapshotOrgId(activeOrgId || sessionStorage.getItem('ACTIVE_ORG_ID'));
      } catch {}
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    e.stopPropagation();

    if (!agentName.trim()) {
      setError('Agent name cannot be empty');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await agentService.createAgent(
        { agent_name: agentName.trim() },
        { scopeOverride: { scope: snapshotScope, organizationId: snapshotOrgId || undefined } }
      );
      setAgentName('');
      onClose();
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      console.error('Failed to create agent:', err);
      setError('Failed to create agent: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    e.stopPropagation();
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleModalContentClick = (e: React.MouseEvent<HTMLDivElement>) => {
    e.stopPropagation();
  };

  if (!isOpen) return null;

  return (
    <Portal>
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50" onClick={handleBackdropClick}>
        <div className="bg-white p-6 rounded-lg shadow-xl max-w-md w-full mx-4" onClick={handleModalContentClick}>
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Add New Agent</h3>
          <div>
            {error && (
              <p className="text-red-600 text-sm mb-3" data-testid="modal-error">{error}</p>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="agentName" className="block text-sm font-medium text-gray-700 mb-2">Agent Name *</label>
                <input
                  id="agentName"
                  name="agentName"
                  type="text"
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  required
                  placeholder="Enter agent name"
                  data-testid="agent-name-input"
                  disabled={loading}
                  autoFocus
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={loading}
                  data-testid="cancel-button"
                  className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !agentName.trim()}
                  data-testid="submit-button"
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Creating...' : 'Create Agent'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </Portal>
  );
};

export default AddAgentModal;
