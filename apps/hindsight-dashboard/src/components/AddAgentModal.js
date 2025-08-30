import React, { useState, useEffect } from 'react';
import agentService from '../api/agentService';
import './AddMemoryBlockModal.css';

const AddAgentModal = ({ isOpen, onClose, onSuccess }) => {
  const [agentName, setAgentName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setAgentName('');
      setError(null);
    }
  }, [isOpen]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (!agentName.trim()) {
      setError('Agent name cannot be empty');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await agentService.createAgent({ agent_name: agentName.trim() });
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
        <h2>Add New Agent</h2>
        <div className="dialog-content">
          {error && <p className="error-message" data-testid="modal-error">{error}</p>}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="agentName">Agent Name *</label>
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
                disabled={loading || !agentName.trim()}
                data-testid="submit-button"
              >
                {loading ? 'Creating...' : 'Create Agent'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AddAgentModal;
