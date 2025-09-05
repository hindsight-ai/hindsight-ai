import React, { useState } from 'react';

const AddAgentDialog = ({ show, onClose, onCreate, loading, error }) => {
  const [agentName, setAgentName] = useState('');

  if (!show) {
    return null;
  }

  const handleSubmit = () => {
    if (agentName.trim()) {
      onCreate(agentName);
      setAgentName(''); // Clear input after submission attempt
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
          <button onClick={onClose} disabled={loading}>Cancel</button>
          <button onClick={handleSubmit} disabled={loading}>
            {loading ? 'Adding...' : 'Add Agent'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AddAgentDialog;
