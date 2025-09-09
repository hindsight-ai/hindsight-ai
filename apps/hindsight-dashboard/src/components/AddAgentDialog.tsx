import React, { useState } from 'react';

interface AddAgentDialogProps {
  show: boolean;
  onClose: () => void;
  onCreate: (name: string) => void;
  loading?: boolean;
  error?: string | null;
}

const AddAgentDialog: React.FC<AddAgentDialogProps> = ({
  show,
  onClose,
  onCreate,
  loading = false,
  error = null,
}) => {
  const [agentName, setAgentName] = useState<string>('');

  if (!show) {
    return null;
  }

  const handleSubmit = () => {
    if (agentName.trim()) {
      onCreate(agentName.trim());
      setAgentName('');
    } else {
      alert('Agent name cannot be empty.');
    }
  };

  return (
    <div className="dialog-overlay">
      <div className="dialog-box">
        <h2>Add New Agent</h2>
        <div className="dialog-content">
          <label htmlFor="agentName">Agent Name:</label>
          <input
            type="text"
            id="agentName"
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            placeholder="Enter agent name"
            disabled={loading}
          />
          <p className="hint">A unique name for your AI agent.</p>
          {error && <p className="error-message">{error}</p>}
        </div>
        <div className="dialog-actions">
          <button onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button onClick={handleSubmit} disabled={loading}>
            {loading ? 'Adding...' : 'Add Agent'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AddAgentDialog;
