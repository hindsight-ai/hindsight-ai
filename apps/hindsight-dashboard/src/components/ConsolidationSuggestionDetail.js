import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getConsolidationSuggestionById, validateConsolidationSuggestion, rejectConsolidationSuggestion } from '../api/memoryService';
import memoryService from '../api/memoryService'; // To fetch original memory blocks

const ConsolidationSuggestionDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [suggestion, setSuggestion] = useState(null);
  const [originalMemories, setOriginalMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSuggestionDetails = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const suggestionData = await getConsolidationSuggestionById(id);
      setSuggestion(suggestionData);

      if (suggestionData && suggestionData.original_memory_ids && suggestionData.original_memory_ids.length > 0) {
        const fetchedOriginalMemories = await Promise.all(
          suggestionData.original_memory_ids.map(memoryId => memoryService.getMemoryBlockById(memoryId))
        );
        setOriginalMemories(fetchedOriginalMemories.filter(Boolean)); // Filter out any null/undefined results
      }
    } catch (err) {
      setError('Failed to load consolidation suggestion details. Error: ' + err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchSuggestionDetails();
  }, [fetchSuggestionDetails]);

  const handleValidate = async () => {
    try {
      await validateConsolidationSuggestion(id);
      alert('Suggestion validated successfully.');
      navigate('/consolidation-suggestions'); // Go back to list after action
    } catch (err) {
      alert(`Failed to validate suggestion. Error: ${err.message}`);
      console.error(err);
    }
  };

  const handleReject = async () => {
    try {
      await rejectConsolidationSuggestion(id);
      alert('Suggestion rejected successfully.');
      navigate('/consolidation-suggestions'); // Go back to list after action
    } catch (err) {
      alert(`Failed to reject suggestion. Error: ${err.message}`);
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
                  <p><strong>Keywords:</strong> {memory.keywords.map(k => k.keyword_text).join(', ')}</p>
                  <p><strong>Created At:</strong> {new Date(memory.created_at).toLocaleString()}</p>
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
