import React, { useState, useEffect, useRef, FC } from 'react';
import { useNavigate } from 'react-router-dom';
import memoryService from '../api/memoryService';
import agentService from '../api/agentService';
import notificationService from '../services/notificationService';
import MemoryBlockDetailModal from './MemoryBlockDetailModal';
import KeywordSuggestionModal from './KeywordSuggestionModal';
import ProcessingDialog from './ProcessingDialog';
import Portal from './Portal';
import CompactionSettingsModal from './CompactionSettingsModal';

interface Suggestion {
  id: string;
  type: 'keywords' | 'compaction' | 'merge' | 'archive';
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  affected_blocks?: string[];
  all_affected_blocks?: string[];
  estimated_impact?: string;
  optimization_details?: any;
  status?: 'completed' | 'pending';
  results?: any;
  affected_blocks_count?: number;
}

import type { Agent } from '../api/agentService';
import type { MemoryBlock } from '../api/memoryService';

interface Filters {
  agentId: string;
  dateRange: string;
  priority: string;
}

interface ProcessMeta {
  processed: number;
  total: number;
  startedAt: number | null;
  etaMs: number;
}

interface DebugBlockResult {
    success: boolean;
    data?: {
        id: string;
        agent_id: string;
        content_preview: string;
    };
    error?: string;
}

interface KeywordSuggestion {
    memory_block_id: string;
    memory_block_content_preview: string;
    current_keywords: string[];
    suggested_keywords: string[];
}

const MemoryOptimizationCenter: FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<string>>(new Set());
  const [executingActions, setExecutingActions] = useState<Set<string>>(new Set());
  const [selectedSuggestion, setSelectedSuggestion] = useState<Suggestion | null>(null);
  const [showDetailModal, setShowDetailModal] = useState<boolean>(false);
  const [filters, setFilters] = useState<Filters>({
    agentId: '',
    dateRange: '',
    priority: ''
  });
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([]);
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [showBlockDetailModal, setShowBlockDetailModal] = useState<boolean>(false);
  
  // Keyword suggestion modal state
  const [showKeywordModal, setShowKeywordModal] = useState<boolean>(false);
  const [keywordSuggestions, setKeywordSuggestions] = useState<KeywordSuggestion[]>([]);
  
  // Compaction settings modal state
  const [showCompactionModal, setShowCompactionModal] = useState<boolean>(false);
  const [compactionSuggestion, setCompactionSuggestion] = useState<Suggestion | null>(null);
  
  // Progress dialog state
  const [processing, setProcessing] = useState<boolean>(false);
  const [processMeta, setProcessMeta] = useState<ProcessMeta>({ processed: 0, total: 0, startedAt: null, etaMs: 0 });
  const abortCtrlRef = useRef<AbortController | null>(null);
  
  // Debug panel state
  const [showDebugPanel, setShowDebugPanel] = useState<boolean>(false);
  const [debugBlockId, setDebugBlockId] = useState<string>('');
  const [debugLoading, setDebugLoading] = useState<boolean>(false);
  const [debugBlockResult, setDebugBlockResult] = useState<DebugBlockResult | null>(null);

  // Fetch AI suggestions for memory optimization
  const fetchSuggestions = async () => {
    setLoading(true);
    try {
      console.log('Fetching optimization suggestions with filters:', filters);
      const response = await memoryService.getMemoryOptimizationSuggestions(filters);
      console.log('Raw API response:', response);
      
      const suggestions: Suggestion[] = response.suggestions || [];
      console.log('Parsed suggestions:', suggestions);
      
      // Log block IDs for debugging
      suggestions.forEach((suggestion, index) => {
        console.log(`Suggestion ${index + 1}:`, {
          id: suggestion.id,
          type: suggestion.type,
          title: suggestion.title,
          affected_blocks_count: suggestion.affected_blocks?.length || 0,
          all_affected_blocks_count: suggestion.all_affected_blocks?.length || 0,
          first_few_blocks: suggestion.affected_blocks?.slice(0, 3),
          first_few_all_blocks: suggestion.all_affected_blocks?.slice(0, 3)
        });
      });
      
      setSuggestions(suggestions);
    } catch (error: any) {
      notificationService.showError('Failed to fetch optimization suggestions');
      console.error('Error fetching suggestions:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch available agents for filtering
  const fetchAvailableAgents = async () => {
    try {
      const response = await agentService.getAgents({ per_page: 1000 });
      if (response && Array.isArray(response.items)) {
        setAvailableAgents(response.items);
      }
    } catch (error: any) {
      console.error('Error fetching agents:', error);
    }
  };

  useEffect(() => {
    fetchSuggestions();
  }, [filters]);

  // Fetch agents only once on component mount
  useEffect(() => {
    fetchAvailableAgents();
  }, []);

  const handleSuggestionToggle = (suggestionId: string) => {
    setSelectedSuggestions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(suggestionId)) {
        newSet.delete(suggestionId);
      } else {
        newSet.add(suggestionId);
      }
      return newSet;
    });
  };

  const handleSuggestionClick = (suggestion: Suggestion) => {
    setSelectedSuggestion(suggestion);
    setShowDetailModal(true);
  };

  const handleFilterChange = (filterType: keyof Filters, value: string) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: value
    }));
  };

  const clearFilters = () => {
    setFilters({
      agentId: '',
      dateRange: '',
      priority: ''
    });
  };

  const handleViewBlockDetails = async (blockId: string) => {
    try {
      console.log('Opening memory block detail modal for:', {
        blockId,
        type: typeof blockId,
        length: blockId?.length
      });
      
      // Validate blockId
      if (!blockId || typeof blockId !== 'string') {
        throw new Error('Invalid block ID format');
      }
      
      // First, let's try to validate that this block actually exists
      console.log('Attempting to verify block exists...');
      try {
        const blockData: MemoryBlock = await memoryService.getMemoryBlockById(blockId);
        console.log('Block verification successful:', {
          id: blockData.id,
          agent_id: blockData.agent_id,
        });
      } catch (verificationError: any) {
        console.error('Block verification failed:', verificationError);
        notificationService.showError(`Memory block not found: ${blockId.slice(0, 20)}... This might be a stale suggestion.`);
        return;
      }
      
      // Open the detail modal
      setSelectedBlockId(blockId);
      setShowBlockDetailModal(true);
    } catch (error: any) {
      console.error('Error opening block details:', error);
      notificationService.showError(`Unable to open memory block details: ${error.message}`);
    }
  };

  const handleExecuteSuggestion = async (suggestion: Suggestion) => {
    // Disable actions while processing
    if (processing) return;
    setExecutingActions(prev => new Set(prev).add(suggestion.id));
    try {
      if (suggestion.type === 'keywords') {
        // Prefer full list if provided by API, fallback to preview list
        const targetIds = suggestion.all_affected_blocks || suggestion.affected_blocks || [];
        if (!targetIds || targetIds.length === 0) {
          notificationService.showWarning('No memory blocks found to process');
          return;
        }

        // Setup processing dialog
        setProcessing(true);
        const startedAt = Date.now();
        setProcessMeta({ processed: 0, total: targetIds.length, startedAt, etaMs: 0 });
        abortCtrlRef.current = new AbortController();

        let resp;
        try {
          // Use batched generation with real progress updates
          resp = await memoryService.bulkGenerateKeywordsBatched(targetIds, {
            batchSize: 200,
            signal: abortCtrlRef.current.signal,
            onProgress: ({ processed, total }: { processed: number, total: number }) => {
              const elapsed = Date.now() - startedAt;
              const rate = processed > 0 && elapsed > 0 ? processed / elapsed : 0; // items per ms
              const remaining = Math.max(0, total - processed);
              const etaMs = rate > 0 ? Math.round(remaining / rate) : 0;
              setProcessMeta({ processed, total, startedAt, etaMs });
            }
          });
        } catch (err: any) {
          if (err.name === 'AbortError') {
            notificationService.showWarning('Keyword generation cancelled');
            return;
          }
          throw err;
        }

        // Mark as complete in dialog
        setProcessMeta((prev) => ({ ...prev, processed: prev.total, etaMs: 0 }));
        setProcessing(false);

        const suggestionsArr = resp?.suggestions || [];
        if (suggestionsArr.length > 0) {
          setKeywordSuggestions(suggestionsArr);
          setShowKeywordModal(true);
          notificationService.showSuccess(
            `Generated keyword suggestions for ${resp.successful_count}/${resp.total_processed} memory blocks`
          );
        } else {
          notificationService.showWarning('No keyword suggestions could be generated for the selected memory blocks');
        }
      } else if (suggestion.type === 'compaction') {
        // For compaction, show settings modal first
        const targetIds = suggestion.all_affected_blocks || suggestion.affected_blocks || [];
        if (!targetIds || targetIds.length === 0) {
          notificationService.showWarning('No memory blocks found to process');
          return;
        }
        
        setCompactionSuggestion(suggestion);
        setShowCompactionModal(true);
        return; // Don't continue with execution, wait for modal confirmation
      } else {
        const result = await memoryService.executeOptimizationSuggestion(suggestion.id);
        notificationService.showSuccess(`Successfully executed: ${suggestion.title}`);
        // Update the suggestion with results
        setSuggestions(prev => prev.map(s =>
          s.id === suggestion.id
            ? { ...s, status: 'completed', results: result }
            : s
        ));
      }
    } catch (error: any) {
      notificationService.showError(`Failed to execute: ${suggestion.title}`);
      console.error('Error executing suggestion:', error);
    } finally {
      setExecutingActions(prev => {
        const newSet = new Set(prev);
        newSet.delete(suggestion.id);
        return newSet;
      });
      // Close processing if still open
      setProcessing(false);
      abortCtrlRef.current = null;
    }
  };

  const handleBulkExecute = async () => {
    const selectedSuggestionsList = suggestions.filter(s => selectedSuggestions.has(s.id));
    
    for (const suggestion of selectedSuggestionsList) {
      await handleExecuteSuggestion(suggestion);
    }
    
    setSelectedSuggestions(new Set());
  };

  const handleKeywordSuggestionsApplied = (result: any) => {
    // Provide detailed feedback to the user
    const results = result?.results || [];
    const totalAdded = results.reduce((sum: number, r: any) => sum + (r.added_keywords?.length || 0), 0);
    const totalSkipped = results.reduce((sum: number, r: any) => sum + (r.skipped_keywords?.length || 0), 0);

    notificationService.showSuccess(
      `Added ${totalAdded} keyword${totalAdded === 1 ? '' : 's'} to ${result.successful_count} memory block${result.successful_count === 1 ? '' : 's'}`
    );

    if (result.failed_count > 0) {
      notificationService.showWarning(
        `Failed to apply keywords to ${result.failed_count} memory block${result.failed_count === 1 ? '' : 's'}`
      );
    } else if (totalSkipped > 0) {
      notificationService.showWarning(
        `Skipped ${totalSkipped} existing keyword association${totalSkipped === 1 ? '' : 's'}`
      );
    }

    // Refresh suggestions to reflect changes (should reduce the keyword suggestions count)
    fetchSuggestions();
    setShowKeywordModal(false);
    setKeywordSuggestions([]);
  };

  const handleCompactionConfirmed = async (settings: { count: number; userInstructions: string; maxConcurrent: number; }) => {
    if (!compactionSuggestion) return;
    
    // Disable actions while processing
    if (processing) return;
    setExecutingActions(prev => new Set(prev).add(compactionSuggestion.id));
    
    try {
      const targetIds = compactionSuggestion.all_affected_blocks || compactionSuggestion.affected_blocks || [];
      const blocksToProcess = targetIds.slice(0, settings.count); // Limit to selected count
      
      if (blocksToProcess.length === 0) {
        notificationService.showWarning('No memory blocks to process');
        return;
      }

      // Setup processing dialog
      setProcessing(true);
      const startedAt = Date.now();
      setProcessMeta({ processed: 0, total: blocksToProcess.length, startedAt, etaMs: 0 });
      abortCtrlRef.current = new AbortController();

      let result;
      let progressInterval: NodeJS.Timeout | null = null;
      try {
        // Start progress simulation immediately
        progressInterval = setInterval(() => {
          setProcessMeta((prev) => {
            if (!prev.startedAt) return prev;
            const elapsed = Date.now() - prev.startedAt;
            // Estimate total time based on block count (more conservative for compaction)
            const estTotalMs = Math.max(blocksToProcess.length * 2000, 15000); // 2 seconds per block minimum
            const pseudoProcessed = Math.min(prev.total - 1, Math.floor((elapsed / estTotalMs) * prev.total));
            const remainingMs = Math.max(0, estTotalMs - elapsed);
            return { ...prev, processed: Math.max(prev.processed, pseudoProcessed), etaMs: remainingMs };
          });
        }, 1000);

        // Call bulk compaction endpoint
        result = await memoryService.bulkCompactMemoryBlocks(
          blocksToProcess, 
          settings.userInstructions || '',
          settings.maxConcurrent || 4,
          abortCtrlRef.current.signal
        );

      } catch (err: any) {
        if (progressInterval) {
          clearInterval(progressInterval);
        }
        if (err.name === 'AbortError') {
          notificationService.showWarning('Compaction cancelled');
          return;
        }
        throw err;
      }

      // Clear progress interval and mark as complete
      if (progressInterval) {
        clearInterval(progressInterval);
      }
      setProcessMeta((prev) => ({ ...prev, processed: prev.total, etaMs: 0 }));
      setProcessing(false);

      notificationService.showSuccess(
        `Successfully compacted ${settings.count} memory block${settings.count === 1 ? '' : 's'}`
      );
      
      // Update the suggestion with results
      setSuggestions(prev => prev.map(s =>
        s.id === compactionSuggestion.id
          ? { ...s, status: 'completed', results: result }
          : s
      ));

      // Refresh suggestions to reflect changes
      fetchSuggestions();
      
    } catch (error: any) {
      notificationService.showError(`Failed to compact memory blocks: ${error.message}`);
      console.error('Error executing compaction:', error);
    } finally {
      setExecutingActions(prev => {
        const newSet = new Set(prev);
        if (compactionSuggestion) {
            newSet.delete(compactionSuggestion.id);
        }
        return newSet;
      });
      // Close processing if still open
      setProcessing(false);
      abortCtrlRef.current = null;
      setCompactionSuggestion(null);
    }
  };

  // Debug function to test individual block IDs
  const testBlockId = async (blockId: string) => {
    if (!blockId.trim()) return;
    
    setDebugLoading(true);
    setDebugBlockResult(null);
    
    try {
      console.log('Testing block ID:', blockId);
      const blockData: MemoryBlock = await memoryService.getMemoryBlockById(blockId);
      setDebugBlockResult({
        success: true,
        data: {
          id: blockData.id,
          agent_id: blockData.agent_id,
          content_preview: (blockData.content || '').slice(0, 100) + '...',
        }
      });
    } catch (error: any) {
      console.error('Block test failed:', error);
      setDebugBlockResult({
        success: false,
        error: error.message
      });
    } finally {
      setDebugLoading(false);
    }
  };

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

  const getSuggestionBadge = (suggestion: Suggestion) => {
    const badgeColors: { [key: string]: string } = {
      high: 'bg-red-100 text-red-800',
      medium: 'bg-yellow-100 text-yellow-800',
      low: 'bg-green-100 text-green-800'
    };

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badgeColors[suggestion.priority] || badgeColors.medium}`}>
        {suggestion.priority || 'medium'} priority
      </span>
    );
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

  // Detailed Suggestion Modal Component
  const DetailModal: FC<{ suggestion: Suggestion | null; isOpen: boolean; onClose: () => void; }> = ({ suggestion, isOpen, onClose }) => {
    if (!isOpen || !suggestion) return null;

    return (
      <Portal>
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm overflow-y-auto h-full w-full z-50">
        <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-md bg-white">
          <div className="mt-3">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                {getSuggestionIcon(suggestion.type)}
                <h3 className="text-xl font-semibold text-gray-900">{suggestion.title}</h3>
                {getSuggestionBadge(suggestion)}
              </div>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600"
              >
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
              <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg">
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
                              onClick={(e) => {
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
                            onClick={(e) => {
                              e.stopPropagation();
                              handleViewBlockDetails(blockId);
                            }}
                            className="px-3 py-1 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
                          >
                            View Details
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              // Alternative: navigate to memory blocks page with search
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
                    handleExecuteSuggestion(suggestion);
                    onClose();
                  }}
                  disabled={executingActions.has(suggestion.id)}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
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

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Memory Optimization Center</h1>
              <p className="mt-2 text-gray-600">
                AI-powered suggestions to improve your memory store
              </p>
            </div>
            <div className="flex items-center gap-4">
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
              {/* Only show debug panel button in development mode */}
              {import.meta.env.VITE_DEV_MODE === 'true' || import.meta.env.DEV && (
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
          <div className="mt-6 bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Filters</h3>
              <button
                onClick={clearFilters}
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
              >
                Clear All
              </button>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {/* Agent Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Agent ID
                </label>
                <select
                  value={filters.agentId}
                  onChange={(e) => handleFilterChange('agentId', e.target.value)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                >
                  <option key="all-agents" value="">All Agents</option>
                  {availableAgents.map((agent, index) => (
                    <option key={agent.agent_id || `agent-${index}`} value={agent.agent_id}>
                      {agent.agent_name || 'Unnamed Agent'}
                    </option>
                  ))}
                </select>
              </div>

              {/* Priority Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Priority
                </label>
                <select
                  value={filters.priority}
                  onChange={(e) => handleFilterChange('priority', e.target.value)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                >
                  <option key="all-priorities" value="">All Priorities</option>
                  <option key="high" value="high">High Priority</option>
                  <option key="medium" value="medium">Medium Priority</option>
                  <option key="low" value="low">Low Priority</option>
                </select>
              </div>

              {/* Date Range Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Date Range
                </label>
                <select
                  value={filters.dateRange}
                  onChange={(e) => handleFilterChange('dateRange', e.target.value)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                >
                  <option key="all-time" value="">All Time</option>
                  <option key="last_7_days" value="last_7_days">Last 7 Days</option>
                  <option key="last_30_days" value="last_30_days">Last 30 Days</option>
                  <option key="last_90_days" value="last_90_days">Last 90 Days</option>
                </select>
              </div>
            </div>
          </div>

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
                  onClick={() => setSelectedSuggestions(new Set())}
                  className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                >
                  Clear Selection
                </button>
                <button
                  onClick={handleBulkExecute}
                  className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700"
                >
                  Execute Selected
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Suggestions List */}
        <div className="space-y-6">
          {suggestions.length === 0 ? (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No optimization suggestions</h3>
              <p className="mt-1 text-sm text-gray-500">
                Your memory store appears to be well-optimized! Check back later for new suggestions.
              </p>
            </div>
          ) : (
            suggestions.map((suggestion) => (
              <div
                key={suggestion.id}
                className={`bg-white shadow rounded-lg overflow-hidden border-l-4 cursor-pointer transition-shadow hover:shadow-lg ${
                  suggestion.priority === 'high' ? 'border-red-400' :
                  suggestion.priority === 'medium' ? 'border-yellow-400' :
                  'border-green-400'
                }`}
                onClick={() => handleSuggestionClick(suggestion)}
              >
                <div className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start">
                      <input
                        type="checkbox"
                        checked={selectedSuggestions.has(suggestion.id)}
                        onChange={(e) => {
                          e.stopPropagation();
                          handleSuggestionToggle(suggestion.id);
                        }}
                        className="mt-1 mr-4 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        disabled={suggestion.status === 'completed'}
                      />
                      <div className="flex-shrink-0 mr-4">
                        {getSuggestionIcon(suggestion.type)}
                      </div>
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
                            {(suggestion.affected_blocks || []).slice(0, 5).map((blockId) => (
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
                              {suggestion.results.summary && (
                                <p>{suggestion.results.summary}</p>
                              )}
                              {suggestion.results.metrics && (
                                <ul className="list-disc list-inside space-y-1">
                                  {Object.entries(suggestion.results.metrics).map(([key, value]) => (
                                    <li key={key}>{key}: {String(value)}</li>
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
                          onClick={(e) => {
                            e.stopPropagation();
                            handleExecuteSuggestion(suggestion);
                          }}
                          disabled={executingActions.has(suggestion.id)}
                          className="inline-flex items-center px-3 py-2 border border-transparent shadow-sm text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                        >
                          {executingActions.has(suggestion.id) ? (
                            <>
                              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Executing...
                            </>
                          ) : (
                            <>
                              <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
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
            ))
          )}
        </div>
      </div>

      {/* Detail Modal */}
      <DetailModal 
        suggestion={selectedSuggestion}
        isOpen={showDetailModal}
        onClose={() => setShowDetailModal(false)}
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
      {import.meta.env.DEV && showDebugPanel && (
        <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-yellow-800">🔧 Debug Panel</h3>
            <button
              onClick={() => setShowDebugPanel(false)}
              className="text-yellow-600 hover:text-yellow-800"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div className="space-y-4">
            {/* Suggestion Info */}
            <div>
              <h4 className="font-medium text-yellow-800 mb-2">Current Suggestions Analysis:</h4>
              <div className="bg-white rounded border p-3 text-sm">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <strong>Total Suggestions:</strong> {suggestions.length}
                  </div>
                  <div>
                    <strong>Total Affected Blocks:</strong> {
                      suggestions.reduce((sum, s) => sum + (s.affected_blocks?.length || 0), 0)
                    }
                  </div>
                </div>
                <div className="mt-2">
                  <strong>Suggestion Types:</strong> {
                    [...new Set(suggestions.map(s => s.type))].join(', ') || 'None'
                  }
                </div>
              </div>
            </div>
            
            {/* Block ID Tester */}
            <div>
              <h4 className="font-medium text-yellow-800 mb-2">Test Block ID:</h4>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={debugBlockId}
                  onChange={(e) => setDebugBlockId(e.target.value)}
                  placeholder="Enter block ID to test..."
                  className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-yellow-500 focus:ring-yellow-500 sm:text-sm"
                />
                <button
                  onClick={() => testBlockId(debugBlockId)}
                  disabled={debugLoading || !debugBlockId.trim()}
                  className="bg-yellow-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-yellow-700 disabled:opacity-50"
                >
                  {debugLoading ? 'Testing...' : 'Test'}
                </button>
              </div>
              
              {/* Quick test buttons for blocks from suggestions */}
              {suggestions.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2">
                  <span className="text-sm text-yellow-700">Quick test:</span>
                  {suggestions.slice(0, 2).map((suggestion, i) => 
                    suggestion.affected_blocks?.slice(0, 2).map((blockId, j) => (
                      <button
                        key={`${i}-${j}`}
                        onClick={() => {
                          setDebugBlockId(blockId);
                          testBlockId(blockId);
                        }}
                        className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded border hover:bg-yellow-200"
                      >
                        {blockId.slice(0, 8)}...
                      </button>
                    ))
                  )}
                </div>
              )}
              
              {/* Test Result */}
              {debugBlockResult && (
                <div className={`p-3 rounded border ${
                  debugBlockResult.success 
                    ? 'bg-green-50 border-green-200 text-green-800' 
                    : 'bg-red-50 border-red-200 text-red-800'
                }`}>
                  {debugBlockResult.success ? (
                    <div>
                      <div className="font-medium mb-2">✅ Block Found!</div>
                      <div className="text-sm space-y-1">
                        {debugBlockResult.data && <>
                            <div><strong>ID:</strong> {debugBlockResult.data.id}</div>
                            <div><strong>Agent:</strong> {debugBlockResult.data.agent_id || 'None'}</div>
                            <div><strong>Content Preview:</strong> {debugBlockResult.data.content_preview}</div>
                        </>}
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="font-medium mb-2">❌ Block Not Found</div>
                      <div className="text-sm">{debugBlockResult.error}</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
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
          try { abortCtrlRef.current?.abort(); } catch {}
          setProcessing(false);
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
        onConfirm={handleCompactionConfirmed}
        suggestion={compactionSuggestion}
        maxBlocks={compactionSuggestion?.all_affected_blocks?.length || compactionSuggestion?.affected_blocks?.length || 0}
      />
    </div>
  );
};

export default MemoryOptimizationCenter;
