import { useState, useEffect, useRef } from 'react';
import memoryService from '../api/memoryService';
import agentService from '../api/agentService';
import notificationService from '../services/notificationService';
import type { Agent } from '../api/agentService';

export interface Suggestion {
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

export interface Filters {
  agentId: string;
  dateRange: string;
  priority: string;
}

export interface ProcessMeta {
  processed: number;
  total: number;
  startedAt: number | null;
  etaMs: number;
}

export interface KeywordSuggestion {
  memory_block_id: string;
  memory_block_content_preview: string;
  current_keywords: string[];
  suggested_keywords: string[];
}

export interface UseMemoryOptimizationReturn {
  // Data
  loading: boolean;
  suggestions: Suggestion[];
  selectedSuggestions: Set<string>;
  executingActions: Set<string>;
  filters: Filters;
  availableAgents: Agent[];
  // Keyword modal
  showKeywordModal: boolean;
  keywordSuggestions: KeywordSuggestion[];
  // Compaction modal
  showCompactionModal: boolean;
  compactionSuggestion: Suggestion | null;
  // Processing dialog
  processing: boolean;
  processMeta: ProcessMeta;
  abortCtrlRef: React.MutableRefObject<AbortController | null>;
  // Actions
  fetchSuggestions: () => Promise<void>;
  handleSuggestionToggle: (id: string) => void;
  handleFilterChange: (filterType: keyof Filters, value: string) => void;
  clearFilters: () => void;
  handleExecuteSuggestion: (suggestion: Suggestion, llmDisabled: boolean) => Promise<void>;
  handleBulkExecute: (llmDisabled: boolean) => Promise<void>;
  handleKeywordSuggestionsApplied: (result: any) => void;
  handleCompactionConfirmed: (settings: { count: number; userInstructions: string; maxConcurrent: number }, llmDisabled: boolean) => Promise<void>;
  clearSelectedSuggestions: () => void;
  setShowKeywordModal: (v: boolean) => void;
  setKeywordSuggestions: (v: KeywordSuggestion[]) => void;
  setShowCompactionModal: (v: boolean) => void;
  setCompactionSuggestion: (v: Suggestion | null) => void;
}

const useMemoryOptimization = (): UseMemoryOptimizationReturn => {
  const [loading, setLoading] = useState<boolean>(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<string>>(new Set());
  const [executingActions, setExecutingActions] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState<Filters>({
    agentId: '',
    dateRange: '',
    priority: '',
  });
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([]);

  // Keyword suggestion modal state
  const [showKeywordModal, setShowKeywordModal] = useState<boolean>(false);
  const [keywordSuggestions, setKeywordSuggestions] = useState<KeywordSuggestion[]>([]);

  // Compaction settings modal state
  const [showCompactionModal, setShowCompactionModal] = useState<boolean>(false);
  const [compactionSuggestion, setCompactionSuggestion] = useState<Suggestion | null>(null);

  // Progress dialog state
  const [processing, setProcessing] = useState<boolean>(false);
  const [processMeta, setProcessMeta] = useState<ProcessMeta>({
    processed: 0,
    total: 0,
    startedAt: null,
    etaMs: 0,
  });
  const abortCtrlRef = useRef<AbortController | null>(null);

  const fetchSuggestions = async () => {
    setLoading(true);
    try {
      console.log('Fetching optimization suggestions with filters:', filters);
      const response = await memoryService.getMemoryOptimizationSuggestions(filters);
      console.log('Raw API response:', response);

      const parsed: Suggestion[] = response.suggestions || [];
      console.log('Parsed suggestions:', parsed);

      parsed.forEach((suggestion, index) => {
        console.log(`Suggestion ${index + 1}:`, {
          id: suggestion.id,
          type: suggestion.type,
          title: suggestion.title,
          affected_blocks_count: suggestion.affected_blocks?.length || 0,
          all_affected_blocks_count: suggestion.all_affected_blocks?.length || 0,
          first_few_blocks: suggestion.affected_blocks?.slice(0, 3),
          first_few_all_blocks: suggestion.all_affected_blocks?.slice(0, 3),
        });
      });

      setSuggestions(parsed);
    } catch (error: any) {
      notificationService.showError('Failed to fetch optimization suggestions');
      console.error('Error fetching suggestions:', error);
    } finally {
      setLoading(false);
    }
  };

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  // Refresh when organization scope changes globally
  useEffect(() => {
    const handler = () => {
      fetchSuggestions();
      fetchAvailableAgents();
    };
    window.addEventListener('orgScopeChanged', handler);
    return () => window.removeEventListener('orgScopeChanged', handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  const handleFilterChange = (filterType: keyof Filters, value: string) => {
    setFilters(prev => ({ ...prev, [filterType]: value }));
  };

  const clearFilters = () => {
    setFilters({ agentId: '', dateRange: '', priority: '' });
  };

  const clearSelectedSuggestions = () => {
    setSelectedSuggestions(new Set());
  };

  const handleExecuteSuggestion = async (suggestion: Suggestion, llmDisabled: boolean) => {
    if (processing) return;
    setExecutingActions(prev => new Set(prev).add(suggestion.id));
    try {
      if (suggestion.type === 'keywords') {
        const targetIds = suggestion.all_affected_blocks || suggestion.affected_blocks || [];
        if (!targetIds || targetIds.length === 0) {
          notificationService.showWarning('No memory blocks found to process');
          return;
        }

        setProcessing(true);
        const startedAt = Date.now();
        setProcessMeta({ processed: 0, total: targetIds.length, startedAt, etaMs: 0 });
        abortCtrlRef.current = new AbortController();

        let resp;
        try {
          resp = await memoryService.bulkGenerateKeywordsBatched(targetIds, {
            batchSize: 200,
            signal: abortCtrlRef.current.signal,
            onProgress: ({ processed, total }: { processed: number; total: number }) => {
              const elapsed = Date.now() - startedAt;
              const rate = processed > 0 && elapsed > 0 ? processed / elapsed : 0;
              const remaining = Math.max(0, total - processed);
              const etaMs = rate > 0 ? Math.round(remaining / rate) : 0;
              setProcessMeta({ processed, total, startedAt, etaMs });
            },
          });
        } catch (err: any) {
          if (err.name === 'AbortError') {
            notificationService.showWarning('Keyword generation cancelled');
            return;
          }
          throw err;
        }

        setProcessMeta(prev => ({ ...prev, processed: prev.total, etaMs: 0 }));
        setProcessing(false);

        const suggestionsArr = resp?.suggestions || [];
        if (suggestionsArr.length > 0) {
          setKeywordSuggestions(suggestionsArr);
          setShowKeywordModal(true);
          notificationService.showSuccess(
            `Generated keyword suggestions for ${resp.successful_count}/${resp.total_processed} memory blocks`
          );
        } else {
          notificationService.showWarning(
            'No keyword suggestions could be generated for the selected memory blocks'
          );
        }
      } else if (suggestion.type === 'compaction') {
        const targetIds = suggestion.all_affected_blocks || suggestion.affected_blocks || [];
        if (!targetIds || targetIds.length === 0) {
          notificationService.showWarning('No memory blocks found to process');
          return;
        }
        if (llmDisabled) {
          notificationService.showInfo('LLM features are currently disabled.');
          return;
        }

        setCompactionSuggestion(suggestion);
        setShowCompactionModal(true);
        return;
      } else {
        const result = await memoryService.executeOptimizationSuggestion(suggestion.id);
        notificationService.showSuccess(`Successfully executed: ${suggestion.title}`);
        setSuggestions(prev =>
          prev.map(s => (s.id === suggestion.id ? { ...s, status: 'completed', results: result } : s))
        );
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
      setProcessing(false);
      abortCtrlRef.current = null;
    }
  };

  const handleBulkExecute = async (llmDisabled: boolean) => {
    const selectedList = suggestions.filter(s => selectedSuggestions.has(s.id));

    if (llmDisabled && selectedList.some(s => s.type === 'compaction')) {
      notificationService.showInfo(
        'LLM features are currently disabled. Remove compaction suggestions to continue.'
      );
      return;
    }

    for (const suggestion of selectedList) {
      await handleExecuteSuggestion(suggestion, llmDisabled);
    }

    setSelectedSuggestions(new Set());
  };

  const handleKeywordSuggestionsApplied = (result: any) => {
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

    fetchSuggestions();
    setShowKeywordModal(false);
    setKeywordSuggestions([]);
  };

  const handleCompactionConfirmed = async (
    settings: { count: number; userInstructions: string; maxConcurrent: number },
    llmDisabled: boolean
  ) => {
    if (llmDisabled) {
      notificationService.showInfo('LLM features are currently disabled.');
      return;
    }
    if (!compactionSuggestion) return;

    if (processing) return;
    setExecutingActions(prev => new Set(prev).add(compactionSuggestion.id));

    try {
      const targetIds = compactionSuggestion.all_affected_blocks || compactionSuggestion.affected_blocks || [];
      const blocksToProcess = targetIds.slice(0, settings.count);

      if (blocksToProcess.length === 0) {
        notificationService.showWarning('No memory blocks to process');
        return;
      }

      setProcessing(true);
      const startedAt = Date.now();
      setProcessMeta({ processed: 0, total: blocksToProcess.length, startedAt, etaMs: 0 });
      abortCtrlRef.current = new AbortController();

      let result;
      let progressInterval: ReturnType<typeof setInterval> | null = null;
      try {
        progressInterval = setInterval(() => {
          setProcessMeta(prev => {
            if (!prev.startedAt) return prev;
            const elapsed = Date.now() - prev.startedAt;
            const estTotalMs = Math.max(blocksToProcess.length * 2000, 15000);
            const pseudoProcessed = Math.min(
              prev.total - 1,
              Math.floor((elapsed / estTotalMs) * prev.total)
            );
            const remainingMs = Math.max(0, estTotalMs - elapsed);
            return { ...prev, processed: Math.max(prev.processed, pseudoProcessed), etaMs: remainingMs };
          });
        }, 1000);

        result = await memoryService.bulkCompactMemoryBlocks(
          blocksToProcess,
          settings.userInstructions || '',
          settings.maxConcurrent || 4,
          abortCtrlRef.current.signal
        );
      } catch (err: any) {
        if (progressInterval) clearInterval(progressInterval);
        if (err.name === 'AbortError') {
          notificationService.showWarning('Compaction cancelled');
          return;
        }
        throw err;
      }

      if (progressInterval) clearInterval(progressInterval);
      setProcessMeta(prev => ({ ...prev, processed: prev.total, etaMs: 0 }));
      setProcessing(false);

      notificationService.showSuccess(
        `Successfully compacted ${settings.count} memory block${settings.count === 1 ? '' : 's'}`
      );

      setSuggestions(prev =>
        prev.map(s =>
          s.id === compactionSuggestion.id ? { ...s, status: 'completed', results: result } : s
        )
      );

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
      setProcessing(false);
      abortCtrlRef.current = null;
      setCompactionSuggestion(null);
    }
  };

  return {
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
    clearSelectedSuggestions,
    handleExecuteSuggestion,
    handleBulkExecute,
    handleKeywordSuggestionsApplied,
    handleCompactionConfirmed,
    setShowKeywordModal,
    setKeywordSuggestions,
    setShowCompactionModal,
    setCompactionSuggestion,
  };
};

export default useMemoryOptimization;
