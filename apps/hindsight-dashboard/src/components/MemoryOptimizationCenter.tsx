import React, { useState, FC } from 'react';
import { VITE_DEV_MODE } from '../lib/viteEnv';
import { useNavigate } from 'react-router-dom';
import memoryService from '../api/memoryService';
import type { MemoryBlock } from '../api/memoryService';
import notificationService from '../services/notificationService';
import MemoryBlockDetailModal from './MemoryBlockDetailModal';
import KeywordSuggestionModal from './KeywordSuggestionModal';
import ProcessingDialog from './ProcessingDialog';
import CompactionSettingsModal from './CompactionSettingsModal';
import OptimizationFilters from './OptimizationFilters';
import SuggestionList from './SuggestionList';
import OptimizationDebugPanel from './OptimizationDebugPanel';
import OptimizationDetailModal from './OptimizationDetailModal';
import useMemoryOptimization from '../hooks/useMemoryOptimization';
import { useAuth } from '../context/AuthContext';
import type { Suggestion } from '../hooks/useMemoryOptimization';

const MemoryOptimizationCenter: FC = () => {
  const { features } = useAuth();
  const llmDisabled = !features.llmEnabled;
  const navigate = useNavigate();

  const {
    loading,
    suggestions,
    selectedSuggestions,
    executingActions,
    filters,
    availableAgents,
    showKeywordModal,
    keywordSuggestions,
    showCompactionModal,
    compactionSuggestion,
    processing,
    processMeta,
    abortCtrlRef,
    fetchSuggestions,
    handleSuggestionToggle,
    handleFilterChange,
    clearFilters,
    handleExecuteSuggestion,
    handleBulkExecute,
    handleKeywordSuggestionsApplied,
    handleCompactionConfirmed,
    clearSelectedSuggestions,
    setShowKeywordModal,
    setKeywordSuggestions,
    setShowCompactionModal,
    setCompactionSuggestion,
  } = useMemoryOptimization();

  // Detail modal state (local — drives a single shared `selectedSuggestion` ref)
  const [selectedSuggestion, setSelectedSuggestion] = useState<Suggestion | null>(null);
  const [showDetailModal, setShowDetailModal] = useState<boolean>(false);

  // Memory block detail modal state
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [showBlockDetailModal, setShowBlockDetailModal] = useState<boolean>(false);

  // Debug panel visibility
  const [showDebugPanel, setShowDebugPanel] = useState<boolean>(false);

  const handleSuggestionClick = (suggestion: Suggestion) => {
    setSelectedSuggestion(suggestion);
    setShowDetailModal(true);
  };

  const handleViewBlockDetails = async (blockId: string) => {
    try {
      console.log('Opening memory block detail modal for:', {
        blockId,
        type: typeof blockId,
        length: blockId?.length,
      });

      if (!blockId || typeof blockId !== 'string') {
        throw new Error('Invalid block ID format');
      }

      console.log('Attempting to verify block exists...');
      try {
        const blockData: MemoryBlock = await memoryService.getMemoryBlockById(blockId);
        console.log('Block verification successful:', {
          id: blockData.id,
          agent_id: blockData.agent_id,
        });
      } catch (verificationError: any) {
        console.error('Block verification failed:', verificationError);
        notificationService.showError(
          `Memory block not found: ${blockId.slice(0, 20)}... This might be a stale suggestion.`
        );
        return;
      }

      setSelectedBlockId(blockId);
      setShowBlockDetailModal(true);
    } catch (error: any) {
      console.error('Error opening block details:', error);
      notificationService.showError(`Unable to open memory block details: ${error.message}`);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Analyzing memory blocks for optimization opportunities...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <h1 className="text-3xl font-bold text-gray-900">Memory Optimization Center</h1>
              <p className="mt-2 text-gray-600">AI-powered suggestions to improve your memory store</p>
              {llmDisabled && (
                <p className="mt-1 text-sm text-gray-500">
                  LLM features are currently disabled. Compaction actions are unavailable.
                </p>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2 sm:gap-4">
              <button
                onClick={fetchSuggestions}
                disabled={loading}
                className="bg-white border border-gray-300 rounded-md px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Refresh Analysis
              </button>
              <button
                onClick={() => navigate('/memory-blocks')}
                className="bg-gray-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-gray-700"
              >
                Back to Memory Blocks
              </button>
              {VITE_DEV_MODE && (
                <button
                  onClick={() => setShowDebugPanel(!showDebugPanel)}
                  className="bg-purple-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-purple-700"
                >
                  Debug Panel
                </button>
              )}
            </div>
          </div>

          {/* Filter Controls */}
          <OptimizationFilters
            filters={filters}
            availableAgents={availableAgents}
            onFilterChange={handleFilterChange}
            onClearFilters={clearFilters}
          />

          {/* Stats */}
          <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-4">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg className="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v6a2 2 0 002 2h2m0 0h2a2 2 0 002-2V7a2 2 0 00-2-2H9m0 0V3h2v2" />
                    </svg>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Total Suggestions</dt>
                      <dd className="text-lg font-medium text-gray-900">{suggestions.length}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg className="h-6 w-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">High Priority</dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {suggestions.filter(s => s.priority === 'high').length}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg className="h-6 w-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Selected</dt>
                      <dd className="text-lg font-medium text-gray-900">{selectedSuggestions.size}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg className="h-6 w-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Completed</dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {suggestions.filter(s => s.status === 'completed').length}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Bulk Actions */}
        {selectedSuggestions.size > 0 && (
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <svg className="w-5 h-5 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-blue-800 font-medium">
                  {selectedSuggestions.size} suggestion{selectedSuggestions.size === 1 ? '' : 's'} selected
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={clearSelectedSuggestions}
                  className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                >
                  Clear Selection
                </button>
                <button
                  onClick={() => handleBulkExecute(llmDisabled)}
                  className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700"
                >
                  Execute Selected
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Suggestions List */}
        <SuggestionList
          suggestions={suggestions}
          selectedSuggestions={selectedSuggestions}
          executingActions={executingActions}
          llmDisabled={llmDisabled}
          onSuggestionClick={handleSuggestionClick}
          onSuggestionToggle={handleSuggestionToggle}
          onExecuteSuggestion={suggestion => handleExecuteSuggestion(suggestion, llmDisabled)}
        />
      </div>

      {/* Detail Modal */}
      <OptimizationDetailModal
        suggestion={selectedSuggestion}
        isOpen={showDetailModal}
        llmDisabled={llmDisabled}
        executingActions={executingActions}
        onClose={() => setShowDetailModal(false)}
        onExecute={suggestion => handleExecuteSuggestion(suggestion, llmDisabled)}
        onViewBlockDetails={handleViewBlockDetails}
      />

      {/* Memory Block Detail Modal */}
      <MemoryBlockDetailModal
        blockId={selectedBlockId}
        isOpen={showBlockDetailModal}
        onClose={() => {
          setShowBlockDetailModal(false);
          setSelectedBlockId(null);
        }}
      />

      {/* Debug Panel - Only show in development mode */}
      {VITE_DEV_MODE && showDebugPanel && (
        <OptimizationDebugPanel
          suggestions={suggestions}
          onClose={() => setShowDebugPanel(false)}
        />
      )}

      {/* Processing dialog for long-running actions */}
      <ProcessingDialog
        isOpen={processing}
        title="Generating keyword suggestions"
        subtitle="This may take a moment for large datasets. You can cancel anytime."
        progress={processMeta.total > 0 ? processMeta.processed / processMeta.total : 0}
        processed={processMeta.processed}
        total={processMeta.total}
        elapsedMs={processMeta.startedAt ? Date.now() - processMeta.startedAt : 0}
        etaMs={processMeta.etaMs}
        cancellable={true}
        onCancel={() => {
          try {
            abortCtrlRef.current?.abort();
          } catch {}
          // processing state will be cleared by the hook's finally block
        }}
      />

      {/* Keyword Suggestion Modal */}
      <KeywordSuggestionModal
        isOpen={showKeywordModal}
        onClose={() => {
          setShowKeywordModal(false);
          setKeywordSuggestions([]);
        }}
        suggestions={keywordSuggestions}
        onApply={handleKeywordSuggestionsApplied}
        disabled={processing}
      />

      {/* Compaction Settings Modal */}
      <CompactionSettingsModal
        isOpen={showCompactionModal}
        onClose={() => {
          setShowCompactionModal(false);
          setCompactionSuggestion(null);
        }}
        onConfirm={settings => handleCompactionConfirmed(settings, llmDisabled)}
        suggestion={compactionSuggestion}
        maxBlocks={
          compactionSuggestion?.all_affected_blocks?.length ||
          compactionSuggestion?.affected_blocks?.length ||
          0
        }
        llmEnabled={features.llmEnabled}
      />
    </div>
  );
};

export default MemoryOptimizationCenter;
