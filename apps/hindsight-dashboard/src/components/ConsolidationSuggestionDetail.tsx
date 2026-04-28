import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getConsolidationSuggestionById, validateConsolidationSuggestion, rejectConsolidationSuggestion } from '../api/memoryService';
import memoryService from '../api/memoryService';
import { UIMemoryBlock } from '../types/domain';
import Button from './Button';

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
        setOriginalMemories(fetchedOriginalMemories.filter(Boolean));
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
      navigate('/consolidation-suggestions');
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
      navigate('/consolidation-suggestions');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to reject suggestion. Error: ${errorMessage}`);
      console.error(err);
    }
  };

  if (loading) {
    return (
      <p className="px-6 py-4 text-sm text-gray-500" data-testid="loading-message">
        Loading suggestion details...
      </p>
    );
  }
  if (error) {
    return (
      <p
        className="mx-6 my-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        data-testid="error-message"
      >
        Error: {error}
      </p>
    );
  }
  if (!suggestion) {
    return (
      <p className="px-6 py-4 text-sm text-gray-500" data-testid="empty-state-message">
        Suggestion not found.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6">
        <h2 className="text-xl font-semibold text-gray-900">Consolidation Suggestion Details</h2>

        <section className="space-y-2">
          <h3 className="text-sm font-medium text-gray-700">Suggested Content</h3>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{suggestion.suggested_content}</p>
        </section>

        <section className="space-y-3">
          <h3 className="text-sm font-medium text-gray-700">
            Original Memories ({originalMemories.length})
          </h3>
          {originalMemories.length > 0 ? (
            <div className="space-y-3">
              {originalMemories.map((memory, index) => (
                <div
                  key={memory.id}
                  className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-2"
                >
                  <h4 className="text-sm font-semibold text-gray-800">
                    Memory Block {index + 1}: {memory.id.slice(0, 8)}…
                  </h4>
                  <p className="text-sm text-gray-700">
                    <strong className="font-medium text-gray-900">Lessons Learned:</strong>{' '}
                    {memory.lessons_learned}
                  </p>
                  <p className="text-sm text-gray-700">
                    <strong className="font-medium text-gray-900">Content:</strong> {memory.content}
                  </p>
                  <p className="text-sm text-gray-700">
                    <strong className="font-medium text-gray-900">Keywords:</strong>{' '}
                    {memory.keywords ? memory.keywords.map((k: any) => k.keyword_text || k.keyword).join(', ') : 'None'}
                  </p>
                  <p className="text-sm text-gray-700">
                    <strong className="font-medium text-gray-900">Created At:</strong>{' '}
                    {memory.created_at ? new Date(memory.created_at).toLocaleString() : 'Unknown'}
                  </p>
                  <Button
                    variant="secondary"
                    onClick={() => navigate(`/memory-blocks/${memory.id}`)}
                    title="View Original Memory Block"
                  >
                    View Original
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No original memories found for this suggestion.</p>
          )}
        </section>

        <footer className="flex flex-wrap gap-3 pt-4 border-t border-gray-200">
          {suggestion.status === 'pending' && (
            <>
              <Button onClick={handleValidate}>Validate Suggestion</Button>
              <Button variant="secondary" onClick={handleReject}>Reject Suggestion</Button>
            </>
          )}
          <Button
            variant="secondary"
            onClick={() => navigate('/consolidation-suggestions')}
            className="ml-auto"
          >
            Back to Suggestions
          </Button>
        </footer>
      </div>
    </div>
  );
};

export default ConsolidationSuggestionDetail;
