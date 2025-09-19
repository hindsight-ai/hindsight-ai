import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import memoryService from '../api/memoryService';
import agentService, { Agent } from '../api/agentService';
import { UIMemoryBlock } from '../types/domain';
import { useAuth } from '../context/AuthContext';
import RefreshIndicator from './RefreshIndicator';
import usePageHeader from '../hooks/usePageHeader';
import ArchivedMemoryCard from './ArchivedMemoryCard';
import MemoryBlockDetailModal from './MemoryBlockDetailModal';
import notificationService from '../services/notificationService';
import StatCard from './StatCard';

interface PaginationState {
  page: number;
  per_page: number;
  total_items: number;
  total_pages: number;
}

const DEFAULT_PAGE_SIZE = 12;

const formatCount = (value: number | undefined): string => {
  if (value == null) return '0';
  return value.toLocaleString();
};

const ArchivedMemoryBlockList: React.FC = () => {
  const { features } = useAuth();
  const featureDisabled = !features.archivedEnabled;
  const navigate = useNavigate();

  const [memoryBlocks, setMemoryBlocks] = useState<UIMemoryBlock[]>([]);
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [actionPendingId, setActionPendingId] = useState<string | null>(null);
  const [detailModalId, setDetailModalId] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState<string>('');
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');
  const [agentFilter, setAgentFilter] = useState<string>('');
  const [conversationFilter, setConversationFilter] = useState<string>('');
  const [sortOption, setSortOption] = useState<'recent' | 'oldest' | 'feedback'>('recent');

  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    per_page: DEFAULT_PAGE_SIZE,
    total_items: 0,
    total_pages: 1
  });

  useEffect(() => {
    const timeout = setTimeout(() => {
      setDebouncedSearch(searchTerm.trim());
    }, 350);
    return () => clearTimeout(timeout);
  }, [searchTerm]);

  const fetchAgents = useCallback(async () => {
    try {
      const response = await agentService.getAgents({ per_page: 500 });
      const agents = Array.isArray(response.items) ? response.items : [];
      setAvailableAgents(agents);
    } catch (err) {
      console.error('Failed to load agents for filter dropdown:', err);
    }
  }, []);

  const fetchArchivedMemoryBlocks = useCallback(async () => {
    if (featureDisabled) {
      setMemoryBlocks([]);
      setLoading(false);
      setError(null);
      setLastUpdated(new Date());
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const skip = (pagination.page - 1) * pagination.per_page;
      const params: Record<string, any> = {
        skip,
        per_page: pagination.per_page,
        sort_by: sortOption === 'feedback' ? 'feedback_score' : 'archived_at',
        sort_order: sortOption === 'oldest' ? 'asc' : 'desc'
      };
      if (debouncedSearch) params.search_query = debouncedSearch;
      if (agentFilter) params.agent_id = agentFilter;
      if (conversationFilter) params.conversation_id = conversationFilter;

      const response = await memoryService.getArchivedMemoryBlocks(params);
      const items = Array.isArray(response.items) ? response.items : [];

      setMemoryBlocks(items);
      setPagination((prev) => ({
        ...prev,
        total_items: response.total_items ?? items.length,
        total_pages:
          response.total_pages ?? Math.max(1, Math.ceil((response.total_items ?? items.length) / prev.per_page))
      }));
      setLastUpdated(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(`Failed to load archived memories: ${message}`);
    } finally {
      setLoading(false);
    }
  }, [featureDisabled, pagination.page, pagination.per_page, sortOption, debouncedSearch, agentFilter, conversationFilter]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  useEffect(() => {
    fetchArchivedMemoryBlocks();
  }, [fetchArchivedMemoryBlocks]);

  const handleManualRefresh = useCallback(() => {
    fetchArchivedMemoryBlocks();
  }, [fetchArchivedMemoryBlocks]);

  const { setHeaderContent, clearHeaderContent } = usePageHeader();

  useEffect(() => {
    setHeaderContent({
      description: 'Review archived memories, restore important insights, or permanently purge data you no longer need.',
      actions: (
        <RefreshIndicator lastUpdated={lastUpdated} onRefresh={handleManualRefresh} loading={loading} />
      )
    });

    return () => clearHeaderContent();
  }, [setHeaderContent, clearHeaderContent, lastUpdated, loading, handleManualRefresh]);

  // Update debounced search results when filters change
  useEffect(() => {
    setPagination((prev) => ({ ...prev, page: 1 }));
  }, [debouncedSearch, agentFilter, conversationFilter, sortOption]);

  const handlePageChange = (newPage: number) => {
    setPagination((prev) => ({
      ...prev,
      page: Math.max(1, Math.min(newPage, prev.total_pages || 1))
    }));
  };

  const handlePerPageChange = (value: number) => {
    setPagination({ page: 1, per_page: value, total_items: 0, total_pages: 1 });
  };

  const agentNameLookup = useMemo(() => {
    const map = new Map<string, string>();
    availableAgents.forEach((agent) => {
      if (agent.agent_id) {
        map.set(agent.agent_id, agent.agent_name || `Agent ${agent.agent_id.slice(-6)}`);
      }
    });
    return map;
  }, [availableAgents]);

  const resolveAgentName = (agentId?: string, fallback?: string) => {
    if (!agentId) return fallback || 'Unknown agent';
    return agentNameLookup.get(agentId) || fallback || `Agent ${agentId.slice(-6)}`;
  };

  const handleViewDetails = (id: string) => {
    setDetailModalId(id);
  };

  const handleRestore = async (id: string) => {
    try {
      setActionPendingId(id);
      await memoryService.updateMemoryBlock(id, { archived: false } as any);
      notificationService.showSuccess('Memory restored successfully');
      await fetchArchivedMemoryBlocks();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      notificationService.showError(`Failed to restore memory: ${message}`);
    } finally {
      setActionPendingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      if (!window.confirm('This will permanently delete the memory block. Continue?')) {
        return;
      }
      setActionPendingId(id);
      await memoryService.deleteMemoryBlock(id);
      notificationService.showSuccess('Memory permanently deleted');
      await fetchArchivedMemoryBlocks();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      notificationService.showError(`Failed to delete memory block: ${message}`);
    } finally {
      setActionPendingId(null);
    }
  };

  const totalArchived = pagination.total_items;
  const uniqueAgentsOnPage = useMemo(() => {
    return new Set(memoryBlocks.map((block) => block.agent_id || '')).size;
  }, [memoryBlocks]);

  const mostRecentArchivedAt = memoryBlocks[0]?.archived_at;

  const showingStart = useMemo(() => {
    if (!totalArchived) return 0;
    return (pagination.page - 1) * pagination.per_page + 1;
  }, [pagination.page, pagination.per_page, totalArchived]);

  const showingEnd = useMemo(() => {
    if (!totalArchived) return 0;
    return Math.min(pagination.page * pagination.per_page, totalArchived);
  }, [pagination.page, pagination.per_page, totalArchived]);

  const emptyState = !loading && !error && memoryBlocks.length === 0;

  const renderSkeletonCards = () => (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <div
          key={index}
          className="h-full rounded-2xl border border-gray-200 bg-white p-6 shadow-sm animate-pulse"
        >
          <div className="h-4 w-32 rounded bg-gray-200" />
          <div className="mt-3 h-6 w-48 rounded bg-gray-200" />
          <div className="mt-4 h-3 w-full rounded bg-gray-200" />
          <div className="mt-2 h-3 w-5/6 rounded bg-gray-200" />
          <div className="mt-2 h-3 w-3/4 rounded bg-gray-200" />
          <div className="mt-6 flex gap-2">
            <div className="h-6 w-20 rounded-full bg-gray-200" />
            <div className="h-6 w-16 rounded-full bg-gray-200" />
          </div>
          <div className="mt-6 h-4 w-40 rounded bg-gray-200" />
        </div>
      ))}
    </div>
  );

  if (featureDisabled) {
    return (
      <div className="mx-auto max-w-3xl rounded-2xl border border-dashed border-gray-300 bg-gray-50 px-6 py-16 text-center text-gray-500">
        <h2 className="text-xl font-semibold text-gray-700">Archived memories</h2>
        <p className="mt-2 text-sm">The archived memories feature is not yet enabled for your workspace.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          title="Archived memories"
          value={totalArchived}
          color="purple"
          loading={loading && !totalArchived}
        />
        <StatCard
          title="Agents represented"
          value={uniqueAgentsOnPage}
          color="blue"
          loading={loading && !memoryBlocks.length}
        />
        <StatCard
          title="Most recent archive"
          value={mostRecentArchivedAt ? new Date(mostRecentArchivedAt).toLocaleDateString() : '—'}
          color="green"
          loading={loading && !memoryBlocks.length}
        />
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="w-full lg:max-w-md">
            <label htmlFor="archived-search" className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Search
            </label>
            <div className="mt-1 flex items-center gap-3">
              <div className="relative flex-1">
                <input
                  id="archived-search"
                  type="search"
                  placeholder="Search archived memories..."
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm text-gray-700 shadow-sm transition focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
                <svg className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-4.35-4.35M9.5 17a7.5 7.5 0 107.5-7.5 7.5 7.5 0 00-7.5 7.5z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="flex w-full flex-col gap-4 sm:flex-row lg:justify-end">
            <div className="w-full sm:w-48">
              <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Agent
              </label>
              <select
                value={agentFilter}
                onChange={(event) => setAgentFilter(event.target.value)}
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

            <div className="w-full sm:w-48">
              <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Conversation ID
              </label>
              <input
                value={conversationFilter}
                onChange={(event) => setConversationFilter(event.target.value)}
                placeholder="Filter by conversation"
                className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
            </div>

            <div className="w-full sm:w-44">
              <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Sort by
              </label>
              <select
                value={sortOption}
                onChange={(event) => setSortOption(event.target.value as typeof sortOption)}
                className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="recent">Recently archived</option>
                <option value="oldest">Oldest archived</option>
                <option value="feedback">Highest feedback score</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        renderSkeletonCards()
      ) : emptyState ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-gray-200 bg-white p-12 text-center shadow-sm">
          <svg className="h-12 w-12 text-gray-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V7m-5 4l-3 3-3-3m3 3V4" />
          </svg>
          <h3 className="mt-4 text-lg font-semibold text-gray-800">No archived memories yet</h3>
          <p className="mt-2 max-w-md text-sm text-gray-500">
            Memories you archive will appear here. Try adjusting your filters or head back to the main memory view to archive specific items.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
         {memoryBlocks.map((block) => (
           <ArchivedMemoryCard
             key={block.id}
             memoryBlock={block}
             agentName={resolveAgentName(block.agent_id, (block as any).agent_name)}
             onView={handleViewDetails}
             onRestore={handleRestore}
             onDelete={handleDelete}
             actionPending={actionPendingId === block.id}
           />
         ))}
       </div>
     )}

      {!loading && !emptyState && pagination.total_pages > 1 && (
        <div className="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm md:flex-row md:items-center md:justify-between">
          <div className="text-sm text-gray-600">
            Showing {showingStart}-{showingEnd} of {formatCount(totalArchived)} archived memories
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => handlePageChange(1)}
                disabled={pagination.page === 1}
                className="rounded-full border border-gray-200 px-3 py-1 text-xs text-gray-600 transition hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-50"
              >
                First
              </button>
              <button
                type="button"
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={pagination.page === 1}
                className="rounded-full border border-gray-200 px-3 py-1 text-xs text-gray-600 transition hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={pagination.page === pagination.total_pages}
                className="rounded-full border border-gray-200 px-3 py-1 text-xs text-gray-600 transition hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
              <button
                type="button"
                onClick={() => handlePageChange(pagination.total_pages)}
                disabled={pagination.page === pagination.total_pages}
                className="rounded-full border border-gray-200 px-3 py-1 text-xs text-gray-600 transition hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Last
              </button>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>Rows:</span>
              <select
                value={pagination.per_page}
                onChange={(event) => handlePerPageChange(Number(event.target.value))}
                className="rounded-lg border border-gray-200 px-2 py-1 text-gray-700 focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-100"
              >
                {[12, 24, 48].map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>
          </div>
       </div>
     )}

      <MemoryBlockDetailModal
        blockId={detailModalId || ''}
        isOpen={Boolean(detailModalId)}
        onClose={() => setDetailModalId(null)}
      />
    </div>
  );
};

export default ArchivedMemoryBlockList;
