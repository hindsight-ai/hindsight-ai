import React, { useState, useEffect } from 'react';
import Portal from './Portal';
import Button from './Button';
import memoryService from '../api/memoryService';
import agentService from '../api/agentService';
import notificationService from '../services/notificationService';
import { Agent } from '../api/agentService';
import { useOrg } from '../context/OrgContext';

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
  const { activeScope, activeOrgId } = useOrg() as any;
  const [snapshotScope, setSnapshotScope] = useState<'personal' | 'organization' | 'public'>('personal');
  const [snapshotOrgId, setSnapshotOrgId] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchAgents();
      fetchKeywords();
      try {
        setSnapshotScope((activeScope as any) || (sessionStorage.getItem('ACTIVE_SCOPE') as any) || 'personal');
        setSnapshotOrgId(activeOrgId || sessionStorage.getItem('ACTIVE_ORG_ID'));
      } catch {}
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
      await memoryService.createMemoryBlock(
        submitData,
        { scopeOverride: { scope: snapshotScope, organizationId: snapshotOrgId || undefined } }
      );
      console.log('Memory block created successfully');

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

  if (!isOpen) return null;

  const inputClasses =
    'block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30 disabled:bg-gray-100 disabled:cursor-not-allowed';
  const labelClasses = 'block text-sm font-medium text-gray-700';

  return (
    <Portal>
      <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-6">
        <div
          className="absolute inset-0 bg-gray-900/50"
          onClick={onClose}
          aria-hidden="true"
        />
        <div
          className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-memory-block-title"
        >
          <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h2 id="add-memory-block-title" className="text-lg font-semibold text-gray-900">
              Add New Memory Block
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

          <form onSubmit={handleSubmit} className="flex flex-col min-h-0 flex-1">
            <div className="px-6 py-5 space-y-5 overflow-y-auto overscroll-contain">
              {error && (
                <p
                  className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
                  data-testid="modal-error"
                >
                  {error}
                </p>
              )}

              <div className="space-y-1.5">
                <label htmlFor="content" className={labelClasses}>
                  Content <span className="text-red-500">*</span>
                </label>
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
                  className={inputClasses}
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="lessons_learned" className={labelClasses}>
                  Lessons Learned <span className="text-red-500">*</span>
                </label>
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
                  className={inputClasses}
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="errors" className={labelClasses}>
                  Errors (Optional)
                </label>
                <textarea
                  id="errors"
                  name="errors"
                  value={formData.errors}
                  onChange={handleInputChange}
                  placeholder="Any errors or issues encountered"
                  rows={2}
                  data-testid="errors-input"
                  disabled={loading}
                  className={inputClasses}
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label htmlFor="agent_id" className={labelClasses}>
                    Agent ID
                  </label>
                  <select
                    id="agent_id"
                    name="agent_id"
                    value={formData.agent_id}
                    onChange={handleInputChange}
                    data-testid="agent-select"
                    disabled={loading}
                    className={inputClasses}
                  >
                    <option value="">Select an agent (optional)</option>
                    {availableAgents.map(agent => (
                      <option key={agent.id} value={agent.id}>
                        {agent.name || agent.id}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="conversation_id" className={labelClasses}>
                    Conversation ID
                  </label>
                  <input
                    type="text"
                    id="conversation_id"
                    name="conversation_id"
                    value={formData.conversation_id}
                    onChange={handleInputChange}
                    placeholder="Optional conversation ID"
                    data-testid="conversation-input"
                    disabled={loading}
                    className={inputClasses}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label htmlFor="feedback_score" className={labelClasses}>
                    Feedback Score
                  </label>
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
                    className={inputClasses}
                  />
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="keywords" className={labelClasses}>
                    Keywords
                  </label>
                  <select
                    id="keywords"
                    name="keywords"
                    multiple
                    value={formData.keywords}
                    onChange={handleKeywordChange}
                    data-testid="keywords-select"
                    disabled={loading}
                    className={`${inputClasses} min-h-[5rem]`}
                  >
                    {availableKeywords.map(keyword => (
                      <option key={keyword} value={keyword}>
                        {keyword}
                      </option>
                    ))}
                  </select>
                  <small className="block text-xs text-gray-500">
                    Hold Ctrl/Cmd to select multiple keywords
                  </small>
                </div>
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
                disabled={loading}
                data-testid="submit-button"
              >
                {loading ? 'Creating...' : 'Create Memory Block'}
              </Button>
            </footer>
          </form>
        </div>
      </div>
    </Portal>
  );
};

export default AddMemoryBlockModal;
