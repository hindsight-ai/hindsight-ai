import React, { useEffect, useState } from 'react';
import Portal from './Portal';
import Button from './Button';
import memoryService from '../api/memoryService';
import { useOrg } from '../context/OrgContext';

interface AddKeywordModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const AddKeywordModal: React.FC<AddKeywordModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [keyword, setKeyword] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const { activeScope, activeOrgId } = useOrg() as any;
  const [snapshotScope, setSnapshotScope] = useState<'personal' | 'organization' | 'public'>('personal');
  const [snapshotOrgId, setSnapshotOrgId] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setKeyword('');
    setError(null);
    try {
      setSnapshotScope((activeScope as any) || (sessionStorage.getItem('ACTIVE_SCOPE') as any) || 'personal');
      setSnapshotOrgId(activeOrgId || sessionStorage.getItem('ACTIVE_ORG_ID'));
    } catch {}
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!keyword.trim()) {
      setError('Keyword cannot be empty');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await memoryService.createKeyword(
        { keyword: keyword.trim() },
        { scopeOverride: { scope: snapshotScope, organizationId: snapshotOrgId || undefined } },
      );
      setKeyword('');
      onClose();
      onSuccess?.();
    } catch (err) {
      console.error('Failed to create keyword:', err);
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError('Failed to create keyword: ' + message);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <Portal>
      <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div
          className="absolute inset-0 bg-gray-900/50"
          onClick={onClose}
          aria-hidden="true"
        />
        <div
          className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden"
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-keyword-title"
        >
          <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h2 id="add-keyword-title" className="text-lg font-semibold text-gray-900">
              Add New Keyword
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition"
              aria-label="Close"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M6 18L18 6" />
              </svg>
            </button>
          </header>

          <form onSubmit={handleSubmit}>
            <div className="px-6 py-5 space-y-4">
              {error && (
                <p
                  className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
                  data-testid="modal-error"
                >
                  {error}
                </p>
              )}
              <div className="space-y-1.5">
                <label htmlFor="keyword" className="block text-sm font-medium text-gray-700">
                  Keyword <span className="text-red-500">*</span>
                </label>
                <input
                  id="keyword"
                  name="keyword"
                  type="text"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  required
                  placeholder="Enter keyword text"
                  data-testid="keyword-input"
                  disabled={loading}
                  autoFocus
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30 disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
            </div>

            <footer className="flex justify-end gap-3 px-6 py-4 bg-gray-50 border-t border-gray-200">
              <Button
                variant="secondary"
                onClick={onClose}
                disabled={loading}
                data-testid="cancel-button"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={loading || !keyword.trim()}
                data-testid="submit-button"
              >
                {loading ? 'Creating...' : 'Create Keyword'}
              </Button>
            </footer>
          </form>
        </div>
      </div>
    </Portal>
  );
};

export default AddKeywordModal;
