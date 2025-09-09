import React, { useState, useEffect } from 'react';
import memoryService from '../api/memoryService';

interface AddKeywordModalProps { isOpen: boolean; onClose: () => void; onSuccess?: () => void; }

const AddKeywordModal: React.FC<AddKeywordModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [keyword, setKeyword] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { if (isOpen) { setKeyword(''); setError(null); } }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); e.stopPropagation();
    if (!keyword.trim()) { setError('Keyword cannot be empty'); return; }
    setLoading(true); setError(null);
    try {
      await memoryService.createKeyword({ keyword: keyword.trim() });
      setKeyword(''); onClose(); onSuccess?.();
    } catch (err) {
      console.error('Failed to create keyword:', err);
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError('Failed to create keyword: ' + message);
    } finally { setLoading(false); }
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => { e.stopPropagation(); if (e.target === e.currentTarget) { onClose(); } };
  const handleModalContentClick = (e: React.MouseEvent<HTMLDivElement>) => { e.stopPropagation(); };

  if (!isOpen) return null;

  return (
    <div className="dialog-overlay" onClick={handleBackdropClick}>
      <div className="dialog-box" onClick={handleModalContentClick}>
        <h2>Add New Keyword</h2>
        <div className="dialog-content">
          {error && <p className="error-message" data-testid="modal-error">{error}</p>}
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="keyword">Keyword *</label>
              <input id="keyword" name="keyword" type="text" value={keyword} onChange={(e) => setKeyword(e.target.value)} required placeholder="Enter keyword text" data-testid="keyword-input" disabled={loading} autoFocus />
            </div>
            <div className="dialog-actions">
              <button type="button" onClick={onClose} disabled={loading} data-testid="cancel-button">Cancel</button>
              <button type="submit" disabled={loading || !keyword.trim()} data-testid="submit-button">{loading ? 'Creating...' : 'Create Keyword'}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AddKeywordModal;
