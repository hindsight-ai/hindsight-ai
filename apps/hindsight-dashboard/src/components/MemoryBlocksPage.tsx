import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import memoryService, { MemoryBlock } from '../api/memoryService';
import agentService, { Agent } from '../api/agentService';
import notificationService from '../services/notificationService';
import MemoryBlockCard from './MemoryBlockCard';
import MemoryBlockDetailModal from './MemoryBlockDetailModal';
import MemoryCompactionModal from './MemoryCompactionModal';
import { UIMemoryBlock } from '../types/domain';
import { useAuth } from '../context/AuthContext';
import RefreshIndicator from './RefreshIndicator';
import usePageHeader from '../hooks/usePageHeader';

// Result structure returned from compaction/compression endpoints (partial / evolving)
interface MemoryCompactionResult {
  compression_ratio: number; // 0..1 ratio of compressed_size/original_size
  compression_quality_score: number; // qualitative 1-10
  original_content?: string;
  original_lessons_learned?: string;
  compressed_content?: string;
  compressed_lessons_learned?: string;
  key_insights_preserved?: string[];
  rationale?: string;
}

interface PaginatedResponse<T> { items: T[]; total_items?: number; total_pages?: number; }

interface PaginationState { page: number; per_page: number; total_items: number; total_pages: number; }

// Derive UI memory block shape (union the API minimal block with UI optional fields)
type MemoryBlockRow = UIMemoryBlock & MemoryBlock & { [k: string]: any };

const MemoryBlocksPage: React.FC = () => {
  const { features } = useAuth();
  const llmDisabled = !features.llmEnabled;
  const [memoryBlocks, setMemoryBlocks] = useState<MemoryBlockRow[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [agentFilter, setAgentFilter] = useState<string>('');
  const [conversationFilter, setConversationFilter] = useState<string>('');
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState<boolean>(false);
  const [selectedMemoryBlockId, setSelectedMemoryBlockId] = useState<string | null>(null);
  const [showCompactionModal, setShowCompactionModal] = useState<boolean>(false);
  const [selectedMemoryBlock, setSelectedMemoryBlock] = useState<MemoryBlockRow | null>(null);

  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    per_page: 12, // More items per page for card layout
    total_items: 0,
    total_pages: 0,
  });

  const debounceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const location = useLocation();
  const navigate = useNavigate();

  // Fetch memory blocks with current filters
  const fetchMemoryBlocks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const skip = (pagination.page - 1) * pagination.per_page;
      const response: PaginatedResponse<MemoryBlockRow> = await memoryService.getMemoryBlocks({
        search_query: searchTerm,
        agent_id: agentFilter,
        conversation_id: conversationFilter,
        skip: skip,
        per_page: pagination.per_page,
        sort_by: 'created_at',
        sort_order: 'desc',
        include_archived: false,
      });

      if (response && Array.isArray(response.items)) {
        setMemoryBlocks(response.items);
      } else {
        setMemoryBlocks([]);
      }

      setPagination(prev => ({
        ...prev,
        total_items: response.total_items || 0,
        total_pages: response.total_pages || 0,
      }));

      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to fetch memory blocks:', err);
      setError('Failed to load memory blocks. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, agentFilter, conversationFilter, pagination.page, pagination.per_page]);

  // Fetch available agents for filter dropdown
  const fetchAgents = useCallback(async () => {
    try {
      const response = await agentService.getAgents({ per_page: 1000 });
      if (response && Array.isArray(response.items)) {
        setAvailableAgents(response.items);
      }
    } catch (err) {
      console.error('Failed to fetch agents:', err);
    }
  }, []);

  // Initialize from URL parameters
  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);
  const rawPage = urlParams.get('page');
  const pageFromUrl = rawPage ? parseInt(rawPage, 10) || 1 : 1;
    const searchFromUrl = urlParams.get('search') || '';
    const agentFromUrl = urlParams.get('agent') || '';
    const conversationFromUrl = urlParams.get('conversation') || '';

    setPagination(prev => ({ ...prev, page: pageFromUrl }));
    setSearchTerm(searchFromUrl);
    setAgentFilter(agentFromUrl);
    setConversationFilter(conversationFromUrl);
  }, [location.search]);

  // Update URL when filters change
  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);
    if (searchTerm) urlParams.set('search', searchTerm);
    else urlParams.delete('search');
    if (agentFilter) urlParams.set('agent', agentFilter);
    else urlParams.delete('agent');
    if (conversationFilter) urlParams.set('conversation', conversationFilter);
    else urlParams.delete('conversation');
    if (pagination.page > 1) urlParams.set('page', pagination.page.toString());
    else urlParams.delete('page');

    const newSearch = urlParams.toString();
    const newPath = `${location.pathname}${newSearch ? `?${newSearch}` : ''}`;
    if (newPath !== `${location.pathname}${location.search}`) {
      navigate(newPath, { replace: true });
    }
  }, [searchTerm, agentFilter, conversationFilter, pagination.page, location.pathname, navigate]);

  // Debounced search
  useEffect(() => {
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }

    debounceTimeoutRef.current = setTimeout(() => {
      if (pagination.page !== 1) {
        setPagination(prev => ({ ...prev, page: 1 }));
      } else {
        fetchMemoryBlocks();
      }
    }, 500);

    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, [searchTerm, agentFilter, conversationFilter]);

  // Initial data fetch
  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  useEffect(() => {
    fetchMemoryBlocks();
  }, [pagination.page]);

  // Refresh when organization scope changes globally
  useEffect(() => {
    const handler = () => {
      try {
        setPagination(prev => ({ ...prev, page: 1 }));
      } catch {}
      fetchAgents();
      fetchMemoryBlocks();
    };
    window.addEventListener('orgScopeChanged', handler);
    return () => window.removeEventListener('orgScopeChanged', handler);
  }, [fetchAgents, fetchMemoryBlocks]);

  // Handle search input change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  // Handle filter changes
  const handleAgentFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setAgentFilter(e.target.value);
  };

  const handleConversationFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setConversationFilter(e.target.value);
  };

  // Handle pagination
  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= pagination.total_pages) {
      setPagination(prev => ({ ...prev, page: newPage }));
    }
  };

  // Handle memory block actions
  const handleViewMemoryBlock = (id: string) => {
    setSelectedMemoryBlockId(id);
    setIsDetailModalOpen(true);
  };

  const handleCloseDetailModal = () => {
    setIsDetailModalOpen(false);
    setSelectedMemoryBlockId(null);
    // Refresh the memory blocks list to reflect any changes
    fetchMemoryBlocks();
  };

  const handleArchiveMemoryBlock = async (id: string) => {
    if (window.confirm('Are you sure you want to archive this memory block?')) {
      try {
        await memoryService.archiveMemoryBlock(id);
        fetchMemoryBlocks();
        notificationService.showSuccess('Memory block archived successfully');
      } catch (err) {
        notificationService.showError('Failed to archive memory block');
      }
    }
  };

  const handleDeleteMemoryBlock = async (id: string) => {
    if (window.confirm('Are you sure you want to permanently delete this memory block? This action cannot be undone.')) {
      try {
        await memoryService.deleteMemoryBlock(id);
        fetchMemoryBlocks();
        notificationService.showSuccess('Memory block deleted successfully');
      } catch (err) {
        notificationService.showError('Failed to delete memory block');
      }
    }
  };

  const handleSuggestKeywords = async (id: string) => {
    try {
      const result = await memoryService.suggestKeywords(id);
      notificationService.showSuccess('Keywords suggested successfully');
      // Refresh the data to show updated keywords
      fetchMemoryBlocks();
    } catch (err) {
      notificationService.showError('Failed to suggest keywords');
      console.error('Error suggesting keywords:', err);
    }
  };

  const handleCompactMemory = async (id: string) => {
    if (llmDisabled) {
      notificationService.showInfo('LLM features are currently disabled.');
      return;
    }
    // Find the memory block and open the compaction modal instead of using primitive confirmation
    const memoryBlock = memoryBlocks.find(block => block.id === id);
    if (memoryBlock) {
      setSelectedMemoryBlock(memoryBlock);
      setShowCompactionModal(true);
    }
  };

  const handleCompactionApplied = (memoryId: string, compactionResult: MemoryCompactionResult) => {
    // Show success notification with compaction details
    notificationService.showSuccess(
      `Memory block compacted successfully! Space saved: ${Math.round((1 - compactionResult.compression_ratio) * 100)}% with ${compactionResult.compression_quality_score}/10 quality score.`,
      8000
    );
    
    // Refresh the data to show updated memory block
    fetchMemoryBlocks();
    
    // Close modal and reset state
    setShowCompactionModal(false);
    setSelectedMemoryBlock(null);
  };

  // Handle header actions
  const handleCreateMemory = () => {
    // This would typically open a modal or navigate to create page
    alert('Create Memory functionality coming soon!');
  };

  const handleFindDuplicates = () => {
    // This would typically open a duplicates finder
    alert('Find Duplicates functionality coming soon!');
  };

  const handleRefresh = useCallback(() => {
    void fetchMemoryBlocks();
    notificationService.showSuccess('Data refreshed successfully');
  }, [fetchMemoryBlocks]);

  // Clear all filters
  const clearFilters = () => {
    setSearchTerm('');
    setAgentFilter('');
    setConversationFilter('');
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const hasActiveFilters = Boolean(searchTerm || agentFilter || conversationFilter);

  const { setHeaderContent, clearHeaderContent } = usePageHeader();

  useEffect(() => {
    setHeaderContent({
      description: 'Search, filter, and review memory blocks across your workspace.',
      actions: (
        <RefreshIndicator
          lastUpdated={lastUpdated}
          onRefresh={handleRefresh}
          loading={loading}
        />
      )
    });

    return () => clearHeaderContent();
  }, [setHeaderContent, clearHeaderContent, lastUpdated, loading, handleRefresh]);

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div className="flex flex-col">
            <label htmlFor="memory-search" className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Search
            </label>
            <div className="relative mt-1">
              <input
                id="memory-search"
                type="search"
                placeholder="Search memories..."
                value={searchTerm}
                onChange={handleSearchChange}
                className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
              <svg className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-4.35-4.35M9.5 17a7.5 7.5 0 107.5-7.5 7.5 7.5 0 00-7.5 7.5z" />
              </svg>
            </div>
          </div>

          <div className="flex flex-col">
            <label htmlFor="memory-agent-filter" className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Agent
            </label>
            <select
              id="memory-agent-filter"
              value={agentFilter}
              onChange={handleAgentFilterChange}
              className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="">All agents</option>
              {availableAgents.map((agent) => (
                <option key={agent.agent_id} value={agent.agent_id}>
                  {agent.agent_name || `Agent ${agent.agent_id?.slice(-6)}`}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col">
            <label htmlFor="memory-conversation-filter" className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Conversation ID
            </label>
            <input
              id="memory-conversation-filter"
              value={conversationFilter}
              onChange={handleConversationFilterChange}
              placeholder="Filter by conversation"
              className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div className="flex flex-col">
            <label htmlFor="memory-sort" className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Sort
            </label>
            <select
              id="memory-sort"
              value={sort.field === 'created_at' ? (sort.order === 'asc' ? 'oldest' : 'recent') : sort.field}
              onChange={(event) => {
                const value = event.target.value;
                if (value === 'recent') {
                  setSort({ field: 'created_at', order: 'desc' });
                } else if (value === 'oldest') {
                  setSort({ field: 'created_at', order: 'asc' });
                } else if (value === 'feedback') {
                  setSort({ field: 'feedback_score', order: 'desc' });
                }
              }}
              className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="recent">Recently created</option>
              <option value="oldest">Oldest first</option>
              <option value="feedback">Highest feedback</option>
            </select>
          </div>
        </div>

        {hasActiveFilters && (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-blue-100 bg-blue-50/60 px-4 py-3 text-sm text-blue-700">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium">Active filters:</span>
              {searchTerm && <span className="rounded-full bg-white px-2 py-1 text-xs text-blue-700">Search "{searchTerm}"</span>}
              {agentFilter && (
                <span className="rounded-full bg-white px-2 py-1 text-xs text-blue-700">
                  Agent {availableAgents.find((a) => a.agent_id === agentFilter)?.agent_name || agentFilter}
                </span>
              )}
              {conversationFilter && (
                <span className="rounded-full bg-white px-2 py-1 text-xs text-blue-700">
                  Conversation {conversationFilter}
                </span>
              )}
            </div>
            <button
              onClick={clearFilters}
              className="text-xs font-medium uppercase tracking-wide text-blue-700 underline decoration-dotted"
            >
              Clear all
            </button>
          </div>
        )}
      </div>

      {/* Results Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm text-gray-600">
            {loading ? 'Loading...' : `${pagination.total_items} memory blocks found`}
          </span>
        </div>
      </div>

      {/* Memory Blocks Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {[...Array(6)].map((_, index) => (
            <div key={index} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 animate-pulse">
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-start gap-4 flex-1">
                  <div className="bg-gray-200 p-3 rounded-lg flex-shrink-0 w-12 h-12"></div>
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 rounded w-32 mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-24"></div>
                  </div>
                </div>
              </div>
              <div className="space-y-3">
                <div className="h-4 bg-gray-200 rounded w-full"></div>
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="flex gap-2">
                  <div className="h-6 bg-gray-200 rounded-full w-16"></div>
                  <div className="h-6 bg-gray-200 rounded-full w-20"></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-12">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md mx-auto">
            <svg className="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <h3 className="text-lg font-medium text-red-800 mb-2">Error Loading Memory Blocks</h3>
            <p className="text-red-700 mb-4">{error}</p>
            <button
              onClick={fetchMemoryBlocks}
              className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      ) : memoryBlocks.length === 0 ? (
        <div className="text-center py-12">
          <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {hasActiveFilters ? 'No Memory Blocks Match Your Filters' : 'No Memory Blocks Found'}
          </h3>
          <p className="text-gray-500 mb-6">
            {hasActiveFilters
              ? 'Try adjusting your filters or clearing them to see all memory blocks.'
              : 'Start by creating your first memory block to see it here.'
            }
          </p>
          {hasActiveFilters ? (
            <button
              onClick={clearFilters}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Clear Filters
            </button>
          ) : (
            <button
              onClick={handleCreateMemory}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Create Memory Block
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {memoryBlocks.map((memoryBlock) => (
              <MemoryBlockCard
                key={memoryBlock.id}
                memoryBlock={memoryBlock}
                onClick={handleViewMemoryBlock}
                onArchive={handleArchiveMemoryBlock}
                onDelete={handleDeleteMemoryBlock}
                onSuggestKeywords={handleSuggestKeywords}
                onCompactMemory={handleCompactMemory}
                availableAgents={availableAgents}
                llmEnabled={features.llmEnabled}
                showHeaderDate={false}
              />
            ))}
          </div>

          {/* Pagination */}
          {pagination.total_pages > 1 && (
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                Showing {((pagination.page - 1) * pagination.per_page) + 1} to {Math.min(pagination.page * pagination.per_page, pagination.total_items)} of {pagination.total_items} results
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handlePageChange(pagination.page - 1)}
                  disabled={pagination.page <= 1}
                  className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <span className="text-sm text-gray-600">
                  Page {pagination.page} of {pagination.total_pages}
                </span>
                <button
                  onClick={() => handlePageChange(pagination.page + 1)}
                  disabled={pagination.page >= pagination.total_pages}
                  className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Detail Modal */}
      <MemoryBlockDetailModal
        blockId={selectedMemoryBlockId}
        isOpen={isDetailModalOpen}
        onClose={handleCloseDetailModal}
      />

      {/* Memory Compaction Modal */}
      <MemoryCompactionModal
        isOpen={showCompactionModal}
        onClose={() => {
          setShowCompactionModal(false);
          setSelectedMemoryBlock(null);
        }}
        memoryBlock={selectedMemoryBlock}
        onCompactionApplied={handleCompactionApplied}
        llmEnabled={features.llmEnabled}
      />
    </div>
  );
};

export default MemoryBlocksPage;
