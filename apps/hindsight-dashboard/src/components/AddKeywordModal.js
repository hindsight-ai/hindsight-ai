import React, { useState, useEffect } from 'react';
import memoryService from '../api/memoryService';
import './AddMemoryBlockModal.css';

const AddKeywordModal = ({ isOpen, onClose, onSuccess }) => {
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setKeyword('');
      setError(null);
    }
  }, [isOpen]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (!keyword.trim()) {
      setError('Keyword cannot be empty');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await memoryService.createKeyword({ keyword: keyword.trim() });
      setKeyword('');
      onClose();
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      console.error('Failed to create keyword:', err);
      setError('Failed to create keyword: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBackdropClick = (e) => {
    e.stopPropagation();
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleModalContentClick = (e) => {
    e.stopPropagation();
  };

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
              />
            </div>

            <div className="dialog-actions">
              <button
                type="button"
                onClick={onClose}
                disabled={loading}
                data-testid="cancel-button"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !keyword.trim()}
                data-testid="submit-button"
              >
                {loading ? 'Creating...' : 'Create Keyword'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AddKeywordModal;
