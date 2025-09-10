import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import memoryService from '../api/memoryService';
import notificationService from '../services/notificationService';
import ProcessingDialog from './ProcessingDialog';

interface KeywordSuggestion {
  memory_block_id: string;
  memory_block_content_preview: string;
  current_keywords: string[];
  suggested_keywords: string[];
}

interface BlockSelection {
  selectedKeywords: Set<string>;
  allSelected: boolean;
}

interface ProcessMeta {
  processed: number;
  total: number;
  startedAt: number | null;
  etaMs: number;
}

interface KeywordSuggestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  suggestions: KeywordSuggestion[];
  onApply?: (result: any) => void;
  disabled?: boolean;
}

const KeywordSuggestionModal: React.FC<KeywordSuggestionModalProps> = ({ isOpen, onClose, suggestions, onApply, disabled = false }) => {
  const [selectedSuggestions, setSelectedSuggestions] = useState<Record<string, BlockSelection>>({});
  const [loading, setLoading] = useState<boolean>(false);
  const [expandedBlocks, setExpandedBlocks] = useState<Set<string>>(new Set());
  const [processing, setProcessing] = useState<boolean>(false);
  const [processMeta, setProcessMeta] = useState<ProcessMeta>({ processed: 0, total: 0, startedAt: null, etaMs: 0 });
  const abortCtrlRef = useRef<AbortController | null>(null);

  // Initialize selected suggestions when modal opens
  useEffect(() => {
    if (isOpen && suggestions) {
      const initialSelections: Record<string, BlockSelection> = {};
      suggestions.forEach(suggestion => {
        initialSelections[suggestion.memory_block_id] = {
          selectedKeywords: new Set(),
          allSelected: false
        };
      });
      setSelectedSuggestions(initialSelections);
    }
  }, [isOpen, suggestions]);

  const toggleKeywordSelection = (blockId: string, keyword: string) => {
    if (disabled || processing) return;
    setSelectedSuggestions(prev => {
      const blockSelection = prev[blockId] || { selectedKeywords: new Set(), allSelected: false };
      const newSelectedKeywords = new Set(blockSelection.selectedKeywords);
      
      if (newSelectedKeywords.has(keyword)) {
        newSelectedKeywords.delete(keyword);
      } else {
        newSelectedKeywords.add(keyword);
      }
      
      const suggestion = suggestions.find(s => s.memory_block_id === blockId);
      const allSelected = suggestion ? newSelectedKeywords.size === suggestion.suggested_keywords.length : false;
      
      return {
        ...prev,
        [blockId]: {
          selectedKeywords: newSelectedKeywords,
          allSelected
        }
      };
    });
  };

  const toggleSelectAll = (blockId: string) => {
    if (disabled || processing) return;
    setSelectedSuggestions(prev => {
      const blockSelection = prev[blockId] || { selectedKeywords: new Set(), allSelected: false };
      const suggestion = suggestions.find(s => s.memory_block_id === blockId);
      
      if (!suggestion) return prev;
      
      if (blockSelection.allSelected) {
        // Deselect all
        return {
          ...prev,
          [blockId]: {
            selectedKeywords: new Set(),
            allSelected: false
          }
        };
      } else {
        // Select all
        return {
          ...prev,
          [blockId]: {
            selectedKeywords: new Set(suggestion.suggested_keywords),
            allSelected: true
          }
        };
      }
    });
  };

  const toggleGlobalSelectAll = () => {
    if (disabled || processing) return;
    const allSelected = suggestions.every(suggestion => 
      selectedSuggestions[suggestion.memory_block_id]?.allSelected
    );
    
    if (allSelected) {
      // Deselect all
      const newSelections: Record<string, BlockSelection> = {};
      suggestions.forEach(suggestion => {
        newSelections[suggestion.memory_block_id] = {
          selectedKeywords: new Set(),
          allSelected: false
        };
      });
      setSelectedSuggestions(newSelections);
    } else {
      // Select all
      const newSelections: Record<string, BlockSelection> = {};
      suggestions.forEach(suggestion => {
        newSelections[suggestion.memory_block_id] = {
          selectedKeywords: new Set(suggestion.suggested_keywords),
          allSelected: true
        };
      });
      setSelectedSuggestions(newSelections);
    }
  };

  const toggleBlockExpanded = (blockId: string) => {
    if (disabled || processing) return;
    setExpandedBlocks(prev => {
      const newSet = new Set(prev);
      if (newSet.has(blockId)) {
        newSet.delete(blockId);
      } else {
        newSet.add(blockId);
      }
      return newSet;
    });
  };

  const getSelectedCount = (): number => {
    return suggestions.reduce((total, suggestion) => {
      const blockSelection = selectedSuggestions[suggestion.memory_block_id];
      return total + (blockSelection?.selectedKeywords.size || 0);
    }, 0);
  };

  const handleApply = async () => {
    if (disabled || processing) return;
    setLoading(true);
    try {
      // Prepare applications array
      const applications = suggestions
        .map(suggestion => {
          const blockSelection = selectedSuggestions[suggestion.memory_block_id];
          const selectedKeywords = Array.from(blockSelection?.selectedKeywords || []);
          
          if (selectedKeywords.length > 0) {
            return {
              memory_block_id: suggestion.memory_block_id,
              selected_keywords: selectedKeywords
            };
          }
          return null;
        })
        .filter(Boolean);

      if (applications.length === 0) {
        notificationService.showWarning('Please select at least one keyword to apply');
        return;
      }

      // Show processing dialog
      setProcessing(true);
      const startedAt = Date.now();
      setProcessMeta({ processed: 0, total: applications.length, startedAt, etaMs: 0 });
      abortCtrlRef.current = new AbortController();

      let result;
      try {
        // Use batched apply with progress updates
        result = await memoryService.bulkApplyKeywordsBatched(applications, {
          batchSize: 200,
          signal: abortCtrlRef.current.signal,
          onProgress: ({ processed, total }: { processed: number; total: number }) => {
            const elapsed = Date.now() - startedAt;
            const rate = processed > 0 && elapsed > 0 ? processed / elapsed : 0; // items per ms
            const remaining = Math.max(0, total - processed);
            const etaMs = rate > 0 ? Math.round(remaining / rate) : 0;
            setProcessMeta({ processed, total, startedAt, etaMs });
          }
        });
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') {
          notificationService.showWarning('Apply cancelled');
          return;
        }
        throw err;
      } finally {
        setProcessing(false);
      }

      notificationService.showSuccess(
        `Successfully applied keywords to ${result.successful_count} memory blocks`
      );
      
      if (result.failed_count > 0) {
        notificationService.showWarning(
          `Failed to apply keywords to ${result.failed_count} memory blocks`
        );
      }

      onApply && onApply(result);
      onClose();
    } catch (error: unknown) {
      console.error('Error applying keywords:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      notificationService.showError('Failed to apply keywords: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const totalSuggestions = suggestions?.length || 0;
  const selectedCount = getSelectedCount();
  const allGloballySelected = suggestions?.every(suggestion => 
    selectedSuggestions[suggestion.memory_block_id]?.allSelected
  ) || false;

  return createPortal(
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      {/* Apply Processing dialog */}
      <ProcessingDialog
        isOpen={processing}
        title="Applying selected keywords"
        subtitle="Updating memory blocks in bulk. You can cancel to stop the request."
        progress={processMeta.total > 0 ? processMeta.processed / processMeta.total : 0}
        processed={processMeta.processed}
        total={processMeta.total}
        elapsedMs={processMeta.startedAt ? Date.now() - processMeta.startedAt : 0}
        etaMs={processMeta.etaMs}
        cancellable={true}
        onCancel={() => {
          try { abortCtrlRef.current?.abort(); } catch {}
          setProcessing(false);
        }}
      />

      <div className="relative top-4 mx-auto p-5 border w-11/12 max-w-6xl shadow-lg rounded-md bg-white mb-4">
        <div className="mt-3">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              <div>
                <h3 className="text-2xl font-semibold text-gray-900">Keyword Suggestions</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Review and select keywords to apply to your memory blocks
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
              disabled={processing}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Summary Stats */}
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div>
                  <span className="text-sm font-medium text-blue-700">Memory Blocks:</span>
                  <span className="ml-2 text-lg font-bold text-blue-900">{totalSuggestions}</span>
                </div>
                <div>
                  <span className="text-sm font-medium text-blue-700">Selected Keywords:</span>
                  <span className="ml-2 text-lg font-bold text-blue-900">{selectedCount}</span>
                </div>
              </div>
              <button
                onClick={toggleGlobalSelectAll}
                disabled={disabled || processing}
                className={`flex items-center gap-2 px-3 py-2 text-sm font-medium border rounded-md ${(disabled || processing) ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed' : 'text-blue-700 bg-blue-100 border-blue-300 hover:bg-blue-200'}`}
              >
                <input
                  type="checkbox"
                  checked={allGloballySelected}
                  onChange={() => {}} // Controlled by button click
                  disabled={disabled || processing}
                  className="rounded border-gray-300 text-blue-600"
                />
                {allGloballySelected ? 'Deselect All' : 'Select All'}
              </button>
            </div>
          </div>

          {/* Suggestions List */}
          <div className="max-h-96 overflow-y-auto space-y-4">
            {!suggestions || suggestions.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500">No keyword suggestions available.</p>
              </div>
            ) : (
              suggestions.map((suggestion) => {
                const blockSelection = selectedSuggestions[suggestion.memory_block_id] || 
                  { selectedKeywords: new Set(), allSelected: false };
                const isExpanded = expandedBlocks.has(suggestion.memory_block_id);
                
                return (
                  <div key={suggestion.memory_block_id} className="border border-gray-200 rounded-lg overflow-hidden">
                    {/* Memory Block Header */}
                    <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 flex-1">
                          <button
                            onClick={() => toggleBlockExpanded(suggestion.memory_block_id)}
                            className="text-gray-400 hover:text-gray-600"
                            disabled={disabled || processing}
                          >
                            <svg 
                              className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`} 
                              fill="none" 
                              stroke="currentColor" 
                              viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                            </svg>
                          </button>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-gray-900">
                                Memory Block
                              </span>
                              <span className="font-mono text-xs text-gray-500 bg-gray-200 px-2 py-1 rounded">
                                {suggestion.memory_block_id.slice(-8)}
                              </span>
                            </div>
                            <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                              {suggestion.memory_block_content_preview}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-sm text-gray-500">
                            {blockSelection.selectedKeywords.size} of {suggestion.suggested_keywords.length} selected
                          </span>
                          <button
                            onClick={() => toggleSelectAll(suggestion.memory_block_id)}
                            disabled={disabled || processing}
                            className={`px-3 py-1 text-sm font-medium rounded border ${(disabled || processing) ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed' : 'text-blue-700 border-blue-300 hover:bg-blue-50'}`}
                          >
                            {blockSelection.allSelected ? 'Deselect All' : 'Select All'}
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Keywords Section */}
                    <div className="p-4">
                      {/* Current Keywords */}
                      {suggestion.current_keywords && suggestion.current_keywords.length > 0 && (
                        <div className="mb-4">
                          <h5 className="text-sm font-medium text-gray-700 mb-2">Current Keywords:</h5>
                          <div className="flex flex-wrap gap-2">
                            {suggestion.current_keywords.map((keyword, index) => (
                              <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                {keyword}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Suggested Keywords */}
                      <div>
                        <h5 className="text-sm font-medium text-gray-700 mb-2">Suggested Keywords:</h5>
                        <div className="flex flex-wrap gap-2">
                          {suggestion.suggested_keywords.map((keyword, index) => {
                            const isSelected = blockSelection.selectedKeywords.has(keyword);
                            const isExisting = suggestion.current_keywords?.includes(keyword);
                            
                            return (
                              <button
                                key={index}
                                onClick={() => !isExisting && toggleKeywordSelection(suggestion.memory_block_id, keyword)}
                                disabled={isExisting || disabled || processing}
                                className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                                  isExisting 
                                    ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed'
                                    : isSelected
                                    ? 'bg-green-100 text-green-800 border-green-300 hover:bg-green-200'
                                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                                }`}
                              >
                                {isSelected && !isExisting && (
                                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                                  </svg>
                                )}
                                {keyword}
                                {isExisting && (
                                  <span className="ml-1 text-xs">(existing)</span>
                                )}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      {/* Expanded Content */}
                      {isExpanded && (
                        <div className="mt-4 pt-4 border-t border-gray-200">
                          <div className="text-sm text-gray-600">
                            <strong>Full Content Preview:</strong>
                            <div className="mt-2 p-3 bg-gray-50 rounded border text-xs font-mono max-h-32 overflow-y-auto">
                              {suggestion.memory_block_content_preview}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-6 border-t border-gray-200 mt-6">
            <div className="text-sm text-gray-500">
              {selectedCount > 0 && (
                <span>Ready to apply {selectedCount} keywords to {
                  Object.values(selectedSuggestions).filter(s => s.selectedKeywords.size > 0).length
                } memory blocks</span>
              )}
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={onClose}
                disabled={disabled || processing}
                className={`px-4 py-2 text-sm font-medium border rounded-md ${(disabled || processing) ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed' : 'text-gray-700 bg-white border-gray-300 hover:bg-gray-50'}`}
              >
                Cancel
              </button>
              <button
                onClick={handleApply}
                disabled={disabled || processing || loading || selectedCount === 0}
                className={`px-4 py-2 text-sm font-medium text-white rounded-md ${(disabled || processing || loading || selectedCount === 0) ? 'bg-green-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700'}`}
              >
                {loading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Applying...
                  </>
                ) : (
                  `Apply Selected Keywords (${selectedCount})`
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default KeywordSuggestionModal;
