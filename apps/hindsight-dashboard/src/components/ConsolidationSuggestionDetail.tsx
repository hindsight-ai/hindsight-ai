import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getConsolidationSuggestionById, validateConsolidationSuggestion, rejectConsolidationSuggestion } from '../api/memoryService';
import memoryService from '../api/memoryService'; // To fetch original memory blocks
import { UIMemoryBlock } from '../types/domain';

interface ConsolidationSuggestion {
  suggestion_id: string;
  status: string;
  suggested_content?: string;
  original_memory_ids?: string[];
}

const ConsolidationSuggestionDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [suggestion, setSuggestion] = useState<ConsolidationSuggestion | null>(null);
  const [originalMemories, setOriginalMemories] = useState<UIMemoryBlock[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSuggestionDetails = useCallback(async (): Promise<void> => {
    if (!id) {
      setError('No suggestion ID provided');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const suggestionData: ConsolidationSuggestion = await getConsolidationSuggestionById(id);
      setSuggestion(suggestionData);

      if (suggestionData && suggestionData.original_memory_ids && suggestionData.original_memory_ids.length > 0) {
        const fetchedOriginalMemories: UIMemoryBlock[] = await Promise.all(
          suggestionData.original_memory_ids.map((memoryId: string) => memoryService.getMemoryBlockById(memoryId))
        );
        setOriginalMemories(fetchedOriginalMemories.filter(Boolean)); // Filter out any null/undefined results
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError('Failed to load consolidation suggestion details. Error: ' + errorMessage);
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchSuggestionDetails();
  }, [fetchSuggestionDetails]);

  const handleValidate = async (): Promise<void> => {
    if (!id) return;

    try {
      await validateConsolidationSuggestion(id);
      alert('Suggestion validated successfully.');
      navigate('/consolidation-suggestions'); // Go back to list after action
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to validate suggestion. Error: ${errorMessage}`);
      console.error(err);
    }
  };

  const handleReject = async (): Promise<void> => {
    if (!id) return;

    try {
      await rejectConsolidationSuggestion(id);
      alert('Suggestion rejected successfully.');
      navigate('/consolidation-suggestions'); // Go back to list after action
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to reject suggestion. Error: ${errorMessage}`);
      console.error(err);
    }
  };

  if (loading) return <p className="loading-message">Loading suggestion details...</p>;
  if (error) return <p className="error-message">Error: {error}</p>;
  if (!suggestion) return <p className="empty-state-message">Suggestion not found.</p>;

  return (
    <div className="memory-block-list-container"> {/* Reusing container style */}
      <div className="data-table-container"> {/* Reusing card style */}
        <h2>Consolidation Suggestion Details</h2>
        <div className="detail-section">
          <h3>Suggested Content</h3>
          <p>{suggestion.suggested_content}</p>
        </div>

        <div className="detail-section">
          <h3>Original Memories ({originalMemories.length})</h3>
          {originalMemories.length > 0 ? (
            <div className="original-memories-list">
              {originalMemories.map((memory, index) => (
                <div key={memory.id} className="memory-block-item">
                  <h4>Memory Block {index + 1}: {memory.id.slice(0, 8)}...</h4>
                  <p><strong>Lessons Learned:</strong> {memory.lessons_learned}</p>
                  <p><strong>Content:</strong> {memory.content}</p>
                  <p><strong>Keywords:</strong> {memory.keywords ? memory.keywords.map((k: any) => k.keyword_text || k.keyword).join(', ') : 'None'}</p>
                  <p><strong>Created At:</strong> {memory.created_at ? new Date(memory.created_at).toLocaleString() : 'Unknown'}</p>
                  {/* Add more details as needed */}
                  <button onClick={() => navigate(`/memory-blocks/${memory.id}`)} className="action-icon-button view-edit-button" title="View Original Memory Block">
                    👁️ View Original
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p>No original memories found for this suggestion.</p>
          )}
        </div>

        <div className="detail-actions">
          {suggestion.status === 'pending' && (
            <>
              <button onClick={handleValidate} className="add-button">Validate Suggestion</button>
              <button onClick={handleReject} className="remove-button">Reject Suggestion</button>
            </>
          )}
          <button onClick={() => navigate('/consolidation-suggestions')} className="secondary-button">Back to Suggestions</button>
        </div>
      </div>
    </div>
  );
};

export default ConsolidationSuggestionDetail;
