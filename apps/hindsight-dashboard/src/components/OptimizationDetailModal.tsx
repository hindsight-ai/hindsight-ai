import React, { FC } from 'react';
import { useNavigate } from 'react-router-dom';
import notificationService from '../services/notificationService';
import Portal from './Portal';
import type { Suggestion } from '../hooks/useMemoryOptimization';
import { getSuggestionBadge } from './SuggestionList';

// Re-exported so the orchestrator can use it without depending on SuggestionList internals
export { getSuggestionBadge };

const getSuggestionIcon = (type: Suggestion['type']) => {
  switch (type) {
    case 'compaction':
      return (
        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      );
    case 'merge':
      return (
        <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
        </svg>
      );
    case 'keywords':
      return (
        <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
        </svg>
      );
    case 'archive':
      return (
        <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 8l6 6 6-6" />
        </svg>
      );
    default:
      return (
        <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
  }
};

interface OptimizationDetailModalProps {
  suggestion: Suggestion | null;
  isOpen: boolean;
  llmDisabled: boolean;
  executingActions: Set<string>;
  onClose: () => void;
  onExecute: (suggestion: Suggestion) => void;
  onViewBlockDetails: (blockId: string) => void;
}

const OptimizationDetailModal: FC<OptimizationDetailModalProps> = ({
  suggestion,
  isOpen,
  llmDisabled,
  executingActions,
  onClose,
  onExecute,
  onViewBlockDetails,
}) => {
  const navigate = useNavigate();

  if (!isOpen || !suggestion) return null;

  return (
    <Portal>
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm overflow-y-auto overscroll-contain h-full w-full z-50">
        <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-md bg-white">
          <div className="mt-3">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                {getSuggestionIcon(suggestion.type)}
                <h3 className="text-xl font-semibold text-gray-900">{suggestion.title}</h3>
                {getSuggestionBadge(suggestion)}
              </div>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Description */}
            <div className="mb-6">
              <h4 className="text-lg font-medium text-gray-900 mb-2">Description</h4>
              <p className="text-gray-600">{suggestion.description}</p>
            </div>

            {/* Estimated Impact */}
            <div className="mb-6">
              <h4 className="text-lg font-medium text-gray-900 mb-2">Estimated Impact</h4>
              <p className="text-gray-600">{suggestion.estimated_impact}</p>
            </div>

            {/* Affected Memory Blocks */}
            <div className="mb-6">
              <h4 className="text-lg font-medium text-gray-900 mb-3">
                Affected Memory Blocks ({suggestion.affected_blocks?.length || 0})
              </h4>
              <div className="max-h-64 overflow-y-auto overscroll-contain border border-gray-200 rounded-lg">
                {(suggestion.affected_blocks || []).length === 0 ? (
                  <div className="p-4 text-center text-gray-500">
                    No memory blocks specified for this suggestion.
                  </div>
                ) : (
                  (suggestion.affected_blocks || []).map((blockId, index) => (
                    <div key={blockId || index} className="p-3 border-b border-gray-100 last:border-b-0">
                      <div className="flex items-center justify-between">
                        <div className="flex-1 mr-3">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm text-gray-800 break-all">{blockId}</span>
                            <button
                              onClick={e => {
                                e.stopPropagation();
                                navigator.clipboard.writeText(blockId);
                                notificationService.showSuccess('Block ID copied to clipboard');
                              }}
                              className="text-gray-400 hover:text-gray-600"
                              title="Copy to clipboard"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                              </svg>
                            </button>
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            Length: {blockId?.length || 0} characters
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={e => {
                              e.stopPropagation();
                              onViewBlockDetails(blockId);
                            }}
                            className="px-3 py-1 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
                          >
                            View Details
                          </button>
                          <button
                            onClick={e => {
                              e.stopPropagation();
                              navigate(`/memory-blocks?search=${encodeURIComponent(blockId)}`);
                            }}
                            className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-md hover:bg-gray-50"
                          >
                            Search in List
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Optimization Details */}
            {suggestion.optimization_details && (
              <div className="mb-6">
                <h4 className="text-lg font-medium text-gray-900 mb-3">Optimization Details</h4>
                <div className="bg-gray-50 rounded-lg p-4">
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                    {JSON.stringify(suggestion.optimization_details, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Results (if completed) */}
            {suggestion.results && (
              <div className="mb-6">
                <h4 className="text-lg font-medium text-gray-900 mb-3">Results</h4>
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  {suggestion.results.summary && (
                    <p className="text-green-700 mb-3">{suggestion.results.summary}</p>
                  )}
                  {suggestion.results.metrics && (
                    <div className="space-y-2">
                      {Object.entries(suggestion.results.metrics).map(([key, value]) => (
                        <div key={key} className="flex justify-between text-sm">
                          <span className="text-green-600 font-medium">{key}:</span>
                          <span className="text-green-700">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Close
              </button>
              {suggestion.status !== 'completed' && (
                <button
                  onClick={() => {
                    if (llmDisabled && suggestion.type === 'compaction') {
                      notificationService.showInfo('LLM features are currently disabled.');
                      return;
                    }
                    onExecute(suggestion);
                    onClose();
                  }}
                  disabled={
                    executingActions.has(suggestion.id) ||
                    (llmDisabled && suggestion.type === 'compaction')
                  }
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
                  title={
                    llmDisabled && suggestion.type === 'compaction'
                      ? 'LLM features are currently disabled'
                      : undefined
                  }
                >
                  {executingActions.has(suggestion.id) ? 'Executing...' : 'Execute Optimization'}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </Portal>
  );
};

export default OptimizationDetailModal;
