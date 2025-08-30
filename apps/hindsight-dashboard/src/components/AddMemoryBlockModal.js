import React, { useState, useEffect } from 'react';
import memoryService from '../api/memoryService';
import agentService from '../api/agentService';
import notificationService from '../services/notificationService';
import './AddMemoryBlockModal.css';

const AddMemoryBlockModal = ({ isOpen, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    content: '',
    lessons_learned: '',
    errors: '',
    agent_id: '',
    conversation_id: '',
    feedback_score: 0,
    keywords: [],
  });

  const [availableAgents, setAvailableAgents] = useState([]);
  const [availableKeywords, setAvailableKeywords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      fetchAgents();
      fetchKeywords();
    }
  }, [isOpen]);

  const fetchAgents = async () => {
    try {
      const response = await agentService.getAgents({ per_page: 100 });
      // Ensure agents are properly formatted as objects with id and name
      const agents = (response.items || []).map(agent => ({
        id: agent.id || agent.agent_id || agent,
        name: agent.name || agent.agent_name || agent.id || agent.agent_id || agent
      }));
      setAvailableAgents(agents);
    } catch (err) {
      console.error('Failed to fetch agents:', err);
    }
  };

  const fetchKeywords = async () => {
    try {
      const response = await memoryService.getKeywords();
      // Handle case where keywords might be objects with keyword_text property
      const keywords = (response || []).map(keyword =>
        typeof keyword === 'string' ? keyword : keyword.keyword_text || keyword.text || keyword
      );
      setAvailableKeywords(keywords);
    } catch (err) {
      console.error('Failed to fetch keywords:', err);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleKeywordChange = (e) => {
    const selectedKeywords = Array.from(e.target.selectedOptions, option => option.value);
    setFormData(prev => ({
      ...prev,
      keywords: selectedKeywords
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    e.stopPropagation(); // Prevent any event bubbling
    setLoading(true);
    setError(null);

    try {
      // Prepare the data for submission
      const submitData = {
        ...formData,
        feedback_score: parseInt(formData.feedback_score) || 0,
        keywords: formData.keywords.join(','),
      };

      console.log('Submitting memory block:', submitData); // Debug log
      await memoryService.createMemoryBlock(submitData);
      console.log('Memory block created successfully'); // Debug log

      // Show success notification
      notificationService.showSuccess('Memory block created successfully');

      // Reset form
      setFormData({
        content: '',
        lessons_learned: '',
        errors: '',
        agent_id: '',
        conversation_id: '',
        feedback_score: 0,
        keywords: [],
      });

      onClose();
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      console.error('Failed to create memory block:', err);
      notificationService.showError('Failed to create memory block: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBackdropClick = (e) => {
    // Prevent event bubbling and ensure we only close on backdrop click
    e.stopPropagation();
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleModalContentClick = (e) => {
    // Prevent clicks inside the modal from closing it
    e.stopPropagation();
  };

  if (!isOpen) return null;

  return (
    <div className="dialog-overlay" onClick={handleBackdropClick}>
      <div className="dialog-box" onClick={handleModalContentClick}>
        <h2>Add New Memory Block</h2>
        <div className="dialog-content">
          {error && <p className="error-message" data-testid="modal-error">{error}</p>}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="content">Content *</label>
              <textarea
                id="content"
                name="content"
                value={formData.content}
                onChange={handleInputChange}
                required
                placeholder="Enter the main content of the memory block"
                rows={4}
                data-testid="content-input"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="lessons_learned">Lessons Learned *</label>
              <textarea
                id="lessons_learned"
                name="lessons_learned"
                value={formData.lessons_learned}
                onChange={handleInputChange}
                required
                placeholder="What lessons were learned from this experience?"
                rows={3}
                data-testid="lessons-input"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="errors">Errors (Optional)</label>
              <textarea
                id="errors"
                name="errors"
                value={formData.errors}
                onChange={handleInputChange}
                placeholder="Any errors or issues encountered"
                rows={2}
                data-testid="errors-input"
                disabled={loading}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="agent_id">Agent ID</label>
                <select
                  id="agent_id"
                  name="agent_id"
                  value={formData.agent_id}
                  onChange={handleInputChange}
                  data-testid="agent-select"
                  disabled={loading}
                >
                  <option value="">Select an agent (optional)</option>
                  {availableAgents.map(agent => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name || agent.id}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="conversation_id">Conversation ID</label>
                <input
                  type="text"
                  id="conversation_id"
                  name="conversation_id"
                  value={formData.conversation_id}
                  onChange={handleInputChange}
                  placeholder="Optional conversation ID"
                  data-testid="conversation-input"
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="feedback_score">Feedback Score</label>
                <input
                  type="number"
                  id="feedback_score"
                  name="feedback_score"
                  value={formData.feedback_score}
                  onChange={handleInputChange}
                  min="0"
                  max="100"
                  placeholder="0-100"
                  data-testid="feedback-input"
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="keywords">Keywords</label>
                <select
                  id="keywords"
                  name="keywords"
                  multiple
                  value={formData.keywords}
                  onChange={handleKeywordChange}
                  data-testid="keywords-select"
                  disabled={loading}
                >
                  {availableKeywords.map(keyword => (
                    <option key={keyword} value={keyword}>
                      {keyword}
                    </option>
                  ))}
                </select>
                <small className="form-help">Hold Ctrl/Cmd to select multiple keywords</small>
              </div>
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
                disabled={loading}
                data-testid="submit-button"
              >
                {loading ? 'Creating...' : 'Create Memory Block'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AddMemoryBlockModal;
