import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { getConsolidationSuggestionById, validateConsolidationSuggestion, rejectConsolidationSuggestion } from '../api/memoryService';
import memoryService from '../api/memoryService';
import { ConsolidationSuggestion } from '../api/memoryService';
import { UIMemoryBlock } from '../types/domain';

// Props interface
interface ConsolidationSuggestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  suggestionId: string | null;
}

const ConsolidationSuggestionModal: React.FC<ConsolidationSuggestionModalProps> = ({ isOpen, onClose, suggestionId }) => {
  const [suggestion, setSuggestion] = useState<ConsolidationSuggestion | null>(null);
  const [originalMemories, setOriginalMemories] = useState<UIMemoryBlock[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && suggestionId) {
      fetchSuggestionDetails();
    }
  }, [isOpen, suggestionId]);

  const fetchSuggestionDetails = async (): Promise<void> => {
    if (!suggestionId) return;
    
    setLoading(true);
    setError(null);
    try {
      const suggestionData = await getConsolidationSuggestionById(suggestionId);
      setSuggestion(suggestionData);

      if (suggestionData && suggestionData.original_memory_ids && suggestionData.original_memory_ids.length > 0) {
        const fetchedOriginalMemories = await Promise.all(
          suggestionData.original_memory_ids.map((memoryId: string) => memoryService.getMemoryBlockById(memoryId))
        );
        setOriginalMemories(fetchedOriginalMemories.filter(Boolean) as UIMemoryBlock[]);
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError('Failed to load consolidation suggestion details. Error: ' + errorMessage);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async (): Promise<void> => {
    if (!suggestionId) return;
    
    try {
      await validateConsolidationSuggestion(suggestionId);
      alert('Suggestion validated successfully.');
      onClose();
      // Refresh the parent component
      window.location.reload();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to validate suggestion. Error: ${errorMessage}`);
      console.error(err);
    }
  };

  const handleReject = async (): Promise<void> => {
    if (!suggestionId) return;
    
    try {
      await rejectConsolidationSuggestion(suggestionId);
      alert('Suggestion rejected successfully.');
      onClose();
      // Refresh the parent component
      window.location.reload();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to reject suggestion. Error: ${errorMessage}`);
      console.error(err);
    }
  };

  // Handle click outside to close
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>): void => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return createPortal(
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-start justify-center z-[9999] p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[85vh] overflow-hidden animate-in fade-in-0 zoom-in-95 duration-200 flex flex-col">
        {/* Header - Fixed at top */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center gap-4">
            <div className="bg-blue-100 p-3 rounded-lg">
              <svg className="w-6 h-6 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">Consolidation Suggestion Details</h2>
              <p className="text-sm text-gray-500">Suggestion ID: {suggestionId?.slice(0, 8)}...</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content - Scrollable */}
        <div className="p-6 overflow-y-auto flex-1 min-h-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading suggestion details...</p>
              </div>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md mx-auto">
                <svg className="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <h3 className="text-lg font-medium text-red-800 mb-2">Error Loading Details</h3>
                <p className="text-red-700 mb-4">{error}</p>
                <button
                  onClick={fetchSuggestionDetails}
                  className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
                >
                  Try Again
                </button>
              </div>
            </div>
          ) : suggestion ? (
            <div className="space-y-6">
              {/* Suggestion Info */}
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-sm font-medium text-gray-500">ID: {suggestion.suggestion_id.toString().slice(0, 8)}...</span>
                  <span className={`text-xs px-2 py-1 rounded-full border ${
                    suggestion.status === 'pending' ? 'bg-yellow-100 text-yellow-800 border-yellow-200' :
                    suggestion.status === 'validated' ? 'bg-green-100 text-green-800 border-green-200' :
                    'bg-red-100 text-red-800 border-red-200'
                  }`}>
                    {suggestion.status === 'pending' ? '⏳' : suggestion.status === 'validated' ? '✅' : '❌'} {suggestion.status}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-600 mb-3">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4M4 7s-.5 1 .5 2M20 7s.5 1-.5 2m-19 5s.5-1-.5-2m19 5s-.5-1 .5-2" />
                  </svg>
                  <span>{suggestion.original_memory_ids?.length || 0} original memories</span>
                </div>
              </div>

              {/* Suggested Content */}
              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-3">Suggested Content</h3>
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">{suggestion.suggested_content}</p>
                </div>
              </div>

              {/* Original Memories */}
              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-3">Original Memories ({originalMemories.length})</h3>
                {originalMemories.length > 0 ? (
                  <div className="space-y-4">
                    {originalMemories.map((memory, index) => (
                      <div key={memory.id} className="bg-white border border-gray-200 rounded-lg p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h4 className="font-medium text-gray-800">Memory Block {index + 1}</h4>
                            <p className="text-sm text-gray-500">ID: {memory.id.slice(0, 8)}...</p>
                          </div>
                          <span className="text-xs text-gray-500">
                            {new Date(memory.created_at || new Date()).toLocaleString('en-US', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </span>
                        </div>

                        {memory.lessons_learned && (
                          <div className="mb-3">
                            <h5 className="text-sm font-medium text-gray-700 mb-1">Lessons Learned:</h5>
                            <p className="text-sm text-gray-600 whitespace-pre-wrap">{memory.lessons_learned}</p>
                          </div>
                        )}

                        {memory.content && (
                          <div className="mb-3">
                            <h5 className="text-sm font-medium text-gray-700 mb-1">Content:</h5>
                            <p className="text-sm text-gray-600 whitespace-pre-wrap">{memory.content}</p>
                          </div>
                        )}

                        {memory.keywords && memory.keywords.length > 0 && (
                          <div>
                            <h5 className="text-sm font-medium text-gray-700 mb-1">Keywords:</h5>
                            <div className="flex flex-wrap gap-2">
                              {memory.keywords.map((keyword, idx) => (
                                <span
                                  key={idx}
                                  className="text-sm font-medium bg-blue-100 text-blue-800 px-3 py-1 rounded-full"
                                >
                                  {typeof keyword === 'string' ? keyword : keyword.keyword_text}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 bg-gray-50 rounded-lg">
                    <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    <p className="text-gray-500">No original memories found for this suggestion.</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500">Suggestion not found.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Close
          </button>
          {suggestion && suggestion.status === 'pending' && (
            <>
              <button
                onClick={handleReject}
                className="px-4 py-2 text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
              >
                Reject
              </button>
              <button
                onClick={handleValidate}
                className="px-4 py-2 text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
              >
                Accept
              </button>
            </>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};

export default ConsolidationSuggestionModal;
