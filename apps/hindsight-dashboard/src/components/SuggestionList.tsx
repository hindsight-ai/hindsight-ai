import React, { FC } from 'react';
import type { Suggestion } from '../hooks/useMemoryOptimization';

interface SuggestionListProps {
  suggestions: Suggestion[];
  selectedSuggestions: Set<string>;
  executingActions: Set<string>;
  llmDisabled: boolean;
  onSuggestionClick: (suggestion: Suggestion) => void;
  onSuggestionToggle: (id: string) => void;
  onExecuteSuggestion: (suggestion: Suggestion) => void;
}

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

export const getSuggestionBadge = (suggestion: Suggestion) => {
  const badgeColors: { [key: string]: string } = {
    high: 'bg-red-100 text-red-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-green-100 text-green-800',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        badgeColors[suggestion.priority] || badgeColors.medium
      }`}
    >
      {suggestion.priority || 'medium'} priority
    </span>
  );
};

const SuggestionList: FC<SuggestionListProps> = ({
  suggestions,
  selectedSuggestions,
  executingActions,
  llmDisabled,
  onSuggestionClick,
  onSuggestionToggle,
  onExecuteSuggestion,
}) => {
  if (suggestions.length === 0) {
    return (
      <div className="text-center py-12">
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No optimization suggestions</h3>
        <p className="mt-1 text-sm text-gray-500">
          Your memory store appears to be well-optimized! Check back later for new suggestions.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {suggestions.map(suggestion => (
        <div
          key={suggestion.id}
          className={`bg-white shadow rounded-lg overflow-hidden border-l-4 cursor-pointer transition-shadow hover:shadow-lg ${
            suggestion.priority === 'high'
              ? 'border-red-400'
              : suggestion.priority === 'medium'
              ? 'border-yellow-400'
              : 'border-green-400'
          }`}
          onClick={() => onSuggestionClick(suggestion)}
        >
          <div className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start">
                <input
                  type="checkbox"
                  checked={selectedSuggestions.has(suggestion.id)}
                  onChange={e => {
                    e.stopPropagation();
                    onSuggestionToggle(suggestion.id);
                  }}
                  className="mt-1 mr-4 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  disabled={suggestion.status === 'completed'}
                />
                <div className="flex-shrink-0 mr-4">{getSuggestionIcon(suggestion.type)}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-medium text-gray-900">{suggestion.title}</h3>
                    {getSuggestionBadge(suggestion)}
                    {suggestion.status === 'completed' && (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        ✓ Completed
                      </span>
                    )}
                  </div>
                  <p className="text-gray-600 mb-4">{suggestion.description}</p>

                  {/* Affected Items Preview */}
                  <div className="mb-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      Affected Memory Blocks ({suggestion.affected_blocks?.length || 0}):
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {(suggestion.affected_blocks || []).slice(0, 5).map(blockId => (
                        <span
                          key={blockId}
                          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
                        >
                          {blockId.slice(-8)}
                        </span>
                      ))}
                      {(suggestion.affected_blocks?.length || 0) > 5 && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          +{(suggestion.affected_blocks?.length || 0) - 5} more
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Click hint */}
                  <div className="text-sm text-blue-600 font-medium">
                    Click for detailed information →
                  </div>

                  {/* Results (if completed) */}
                  {suggestion.results && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4 mt-4">
                      <h4 className="text-sm font-medium text-green-800 mb-2">Results:</h4>
                      <div className="space-y-1 text-sm text-green-700">
                        {suggestion.results.summary && <p>{suggestion.results.summary}</p>}
                        {suggestion.results.metrics && (
                          <ul className="list-disc list-inside space-y-1">
                            {Object.entries(suggestion.results.metrics).map(([key, value]) => (
                              <li key={key}>
                                {key}: {String(value)}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Estimated Impact */}
                  <div className="text-sm text-gray-500 mt-4">
                    <span className="font-medium">Estimated impact:</span> {suggestion.estimated_impact}
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <div className="flex-shrink-0 ml-4">
                {suggestion.status === 'completed' ? (
                  <span className="inline-flex items-center px-3 py-2 border border-green-300 shadow-sm text-sm leading-4 font-medium rounded-md text-green-700 bg-green-50">
                    <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                    </svg>
                    Completed
                  </span>
                ) : (
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      if (llmDisabled && suggestion.type === 'compaction') {
                        return;
                      }
                      onExecuteSuggestion(suggestion);
                    }}
                    disabled={
                      executingActions.has(suggestion.id) ||
                      (llmDisabled && suggestion.type === 'compaction')
                    }
                    className="inline-flex items-center px-3 py-2 border border-transparent shadow-sm text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                    title={
                      llmDisabled && suggestion.type === 'compaction'
                        ? 'LLM features are currently disabled'
                        : undefined
                    }
                  >
                    {executingActions.has(suggestion.id) ? (
                      <>
                        <svg
                          className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                          fill="none"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          ></circle>
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          ></path>
                        </svg>
                        Executing...
                      </>
                    ) : (
                      <>
                        <svg
                          className="w-4 h-4 mr-1.5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="2"
                            d="M13 10V3L4 14h7v7l9-11h-7z"
                          />
                        </svg>
                        Execute
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default SuggestionList;
