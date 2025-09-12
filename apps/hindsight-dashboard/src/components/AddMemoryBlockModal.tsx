import React, { useState, useEffect } from 'react';
import Portal from './Portal';
import memoryService from '../api/memoryService';
import agentService from '../api/agentService';
import notificationService from '../services/notificationService';
import { Agent } from '../api/agentService';

const API_BASE_URL = '/api';

interface AddMemoryBlockModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

interface FormData {
  content: string;
  lessons_learned: string;
  errors: string;
  agent_id: string;
  conversation_id: string;
  feedback_score: number;
  keywords: string[];
}

interface AgentOption {
  id: string;
  name: string;
}

const AddMemoryBlockModal: React.FC<AddMemoryBlockModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [formData, setFormData] = useState<FormData>({
    content: '',
    lessons_learned: '',
    errors: '',
    agent_id: '',
    conversation_id: '',
    feedback_score: 0,
    keywords: [],
  });

  const [availableAgents, setAvailableAgents] = useState<AgentOption[]>([]);
  const [availableKeywords, setAvailableKeywords] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchAgents();
      fetchKeywords();
    }
  }, [isOpen]);

  const fetchAgents = async (): Promise<void> => {
    try {
      const response = await agentService.getAgents({ per_page: 100 });
      // Ensure agents are properly formatted as objects with id and name
      const agents: AgentOption[] = (response.items || []).map((agent: Agent) => ({
        id: agent.agent_id,
        name: agent.agent_name
      }));
      setAvailableAgents(agents);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('Failed to fetch agents:', errorMessage);
    }
  };

  const fetchKeywords = async (): Promise<void> => {
    try {
      const response = await memoryService.getKeywords();
      // Handle case where keywords might be objects with keyword_text property
      const keywords: string[] = (response || []).map((keyword: any) =>
        typeof keyword === 'string' ? keyword : keyword.keyword_text || keyword.text || keyword
      );
      setAvailableKeywords(keywords);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('Failed to fetch keywords:', errorMessage);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>): void => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'feedback_score' ? parseInt(value) || 0 : value
    }));
  };

  const handleKeywordChange = (e: React.ChangeEvent<HTMLSelectElement>): void => {
    const selectedKeywords = Array.from(e.target.selectedOptions, (option: HTMLOptionElement) => option.value);
    setFormData(prev => ({
      ...prev,
      keywords: selectedKeywords
    }));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    e.stopPropagation(); // Prevent any event bubbling
    setLoading(true);
    setError(null);

    try {
      // Prepare the data for submission
      const submitData = {
        ...formData,
        feedback_score: formData.feedback_score,
        keywords: formData.keywords.join(','),
      };

      console.log('Submitting memory block:', submitData); // Debug log
      // TODO: Add createMemoryBlock method to memoryService
      const resp = await fetch(`${API_BASE_URL}/memory-blocks/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(submitData),
        credentials: 'include'
      });
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      await resp.json();
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
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('Failed to create memory block:', errorMessage);
      notificationService.showError('Failed to create memory block: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>): void => {
    // Prevent event bubbling and ensure we only close on backdrop click
    e.stopPropagation();
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleModalContentClick = (e: React.MouseEvent<HTMLDivElement>): void => {
    // Prevent clicks inside the modal from closing it
    e.stopPropagation();
  };

  if (!isOpen) return null;

  return (
    <Portal>
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
    </Portal>
  );
};

export default AddMemoryBlockModal;
