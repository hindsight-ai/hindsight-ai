import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import memoryService from '../api/memoryService';
import agentService from '../api/agentService'; // Import agentService
import MemoryBlockFilterBar from './MemoryBlockFilterBar';
import MemoryBlockTable from './MemoryBlockTable';
import PaginationControls from './PaginationControls';
import { UIMemoryBlock, UIMemoryKeyword } from '../types/domain';
import { Agent } from '../api/agentService';
import { useAuth } from '../context/AuthContext';

// Interfaces for component state
interface FiltersState {
  search_query: string;
  agent_id: string;
  conversation_id: string;
  feedback_score_range: [number, number];
  retrieval_count_range: [number, number];
  start_date: string;
  end_date: string;
  keywords: string[];
  search_type: string;
  min_score: string;
  similarity_threshold: string;
  fulltext_weight: string;
  semantic_weight: string;
  min_combined_score: string;
}

interface PaginationState {
  page: number;
  per_page: number;
  total_items: number;
  total_pages: number;
}

interface SortState {
  field: string;
  order: 'asc' | 'desc';
}

const ArchivedMemoryBlockList = () => {
  const { features } = useAuth();
  const featureDisabled = !features.archivedEnabled;
  const [memoryBlocks, setMemoryBlocks] = useState<UIMemoryBlock[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [agentIdInput, setAgentIdInput] = useState<string>(''); // Local state for agent ID input
  const [filters, setFilters] = useState<FiltersState>({
    search_query: '',
    agent_id: '',
    conversation_id: '',
    feedback_score_range: [0, 100],
    retrieval_count_range: [0, 1000],
    start_date: '',
    end_date: '',
    keywords: [],
    search_type: 'fulltext',
    min_score: '',
    similarity_threshold: '',
    fulltext_weight: '',
    semantic_weight: '',
    min_combined_score: '',
  });
  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    per_page: 10,
    total_items: 0,
    total_pages: 0,
  });
  const [sort, setSort] = useState<SortState>({
    field: 'created_at',
    order: 'desc',
  });
  const [pageInputValue, setPageInputValue] = useState<string>('1'); // Local state for page input
  const [availableKeywords, setAvailableKeywords] = useState<UIMemoryKeyword[]>([]);
  const [selectedMemoryBlocks, setSelectedMemoryBlocks] = useState<string[]>([]); // Keep for consistency, but bulk actions won't be used
  const [showFilters, setShowFilters] = useState<boolean>(true);
  const [availableAgentIds, setAvailableAgentIds] = useState<string[]>([]); // New state for agent IDs

  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const fetchArchivedMemoryBlocks = useCallback(async () => {
    if (featureDisabled) {
      setMemoryBlocks([]);
      setLoading(false);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // Convert page-based pagination to offset-based pagination for backend API
      const skip = (pagination.page - 1) * pagination.per_page;
      const response = await memoryService.getArchivedMemoryBlocks({
        ...filters,
        min_feedback_score: filters.feedback_score_range[0],
        max_feedback_score: filters.feedback_score_range[1],
        min_retrieval_count: filters.retrieval_count_range[0],
        max_retrieval_count: filters.retrieval_count_range[1],
        skip: skip,
        per_page: pagination.per_page,
        sort_by: sort.field,
        sort_order: sort.order,
        keywords: filters.keywords.join(','),
      });
      setMemoryBlocks(response.items);
      setPagination((prevPagination) => ({
        ...prevPagination,
        total_items: response.total_items,
        total_pages: response.total_pages,
      }));
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError('Failed to fetch archived memory blocks: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.page, pagination.per_page, sort, featureDisabled]);

  const fetchKeywords = useCallback(async () => {
    try {
      const response = await memoryService.getKeywords();
      setAvailableKeywords(response);
    } catch (err) {
      console.error('Failed to fetch keywords:', err);
    }
  }, []);

  const fetchAgentIds = useCallback(async () => {
    try {
      const response = await agentService.getAgents({ per_page: 1000 }); // Fetch a reasonable number of agents
      setAvailableAgentIds(response.items.map((agent: Agent) => agent.agent_id));
    } catch (err) {
      console.error('Failed to fetch agent IDs:', err);
    }
  }, []);

  useEffect(() => {
    setSelectedMemoryBlocks([]);
  }, [memoryBlocks]);

  const location = useLocation();
  const navigate = useNavigate();

  // Initialize pagination state from URL parameters
  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);
    const pageFromUrl = parseInt(urlParams.get('page') || '1') || 1;
    const perPageFromUrl = parseInt(urlParams.get('per_page') || '10') || 10;

    setPagination((prevPagination) => ({
      ...prevPagination,
      page: pageFromUrl,
      per_page: perPageFromUrl,
    }));
  }, [location.search]);

  useEffect(() => {
    setMemoryBlocks([]);
    setLoading(true);
    fetchArchivedMemoryBlocks();
    fetchKeywords();
    fetchAgentIds();
  }, [filters, pagination.page, pagination.per_page, sort, location.pathname, fetchArchivedMemoryBlocks, fetchKeywords, fetchAgentIds]);

  // Refresh when organization scope changes globally
  useEffect(() => {
    const handler = () => {
      setPagination(prev => ({ ...prev, page: 1 }));
      setMemoryBlocks([]);
      setLoading(true);
      fetchArchivedMemoryBlocks();
      fetchKeywords();
      fetchAgentIds();
    };
    window.addEventListener('orgScopeChanged', handler);
    return () => window.removeEventListener('orgScopeChanged', handler);
  }, [fetchArchivedMemoryBlocks, fetchKeywords, fetchAgentIds]);

  // Update URL parameters when pagination state changes
  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);

    // Only update URL if pagination values are different from URL
    const currentPage = parseInt(urlParams.get('page') || '1') || 1;
    const currentPerPage = parseInt(urlParams.get('per_page') || '10') || 10;

    if (pagination.page !== currentPage || pagination.per_page !== currentPerPage) {
      urlParams.set('page', pagination.page.toString());
      urlParams.set('per_page', pagination.per_page.toString());

      // Preserve other existing parameters
      const newSearch = urlParams.toString();
      navigate(`${location.pathname}?${newSearch}`, { replace: true });
    }
  }, [pagination.page, pagination.per_page, location.pathname, location.search, navigate]);

  useEffect(() => {
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }

    debounceTimeoutRef.current = setTimeout(() => {
      setFilters((prevFilters) => ({
        ...prevFilters,
        search_query: searchTerm,
      }));
    }, 500);

    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, [searchTerm]);

  const toggleFilters = () => {
    setShowFilters(!showFilters);
  };

  // Helper function to validate UUID format
  const isValidUUID = (uuidString: string): boolean => {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuidString);
  };

  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>): void => {
    const { name, value } = e.target;
    if (name === 'search') {
      setSearchTerm(value);
    } else if (name === 'agent_id') {
      setAgentIdInput(value);
    } else {
      setFilters((prevFilters) => ({
        ...prevFilters,
        [name]: value,
      }));
    }
  };

  const handleAgentIdApply = (agentId: string): void => {
    if (agentId === '' || isValidUUID(agentId)) {
      setError(null);
      setFilters((prevFilters) => ({
        ...prevFilters,
        agent_id: agentId,
      }));
      setAgentIdInput(agentId);
    } else {
      setError('Invalid Agent ID format. Please enter a valid UUID or select from suggestions.');
      setFilters((prevFilters) => ({
        ...prevFilters,
        agent_id: '',
      }));
      setAgentIdInput('');
    }
  };

  const handleRangeFilterChange = (name: string, value: number | [number, number]): void => {
    setFilters((prevFilters) => ({
      ...prevFilters,
      [name]: value,
    }));
  };

  const handleKeywordChange = (selectedKeywords: string[]): void => {
    setFilters((prevFilters) => ({
      ...prevFilters,
      keywords: selectedKeywords,
    }));
  };

  const handleSortChange = (field: string): void => {
    setSort((prevSort) => ({
      field,
      order: prevSort.field === field && prevSort.order === 'asc' ? 'desc' : 'asc',
    }));
  };

  const handlePerPageChange = (e: React.ChangeEvent<HTMLSelectElement>): void => {
    setPagination((prevPagination) => ({
      ...prevPagination,
      per_page: parseInt(e.target.value),
      page: 1,
    }));
    // The useEffect will handle triggering fetchArchivedMemoryBlocks when pagination state changes
  };

  const handlePageChange = (newPage: number): void => {
    const totalPages = pagination.total_pages;
    if (newPage >= 1 && newPage <= totalPages) {
      setPagination((prevPagination) => ({
        ...prevPagination,
        page: newPage,
      }));
    }
  };

  const handlePageInputChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    // Only update the local input value, don't trigger fetch
    setPageInputValue(e.target.value);
  };

  const handlePageInputKeyPress = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter') {
      handlePageInputSubmit();
    }
  };

  const handlePageInputBlur = (): void => {
    handlePageInputSubmit();
  };

  const handlePageInputSubmit = (): void => {
    const page = parseInt(pageInputValue);
    const totalPages = pagination.total_pages;
    if (!isNaN(page) && page >= 1 && page <= totalPages) {
      handlePageChange(page);
    } else {
      // Reset to current page if invalid
      setPageInputValue(pagination.page.toString());
    }
  };

  const handleSelectMemoryBlock = (id: string): void => {
    setSelectedMemoryBlocks((prevSelected) =>
      prevSelected.includes(id)
        ? prevSelected.filter((blockId) => blockId !== id)
        : [...prevSelected, id]
    );
  };

  const handleSelectAllMemoryBlocks = (e: React.ChangeEvent<HTMLInputElement>): void => {
    if (e.target.checked) {
      const allBlockIds = memoryBlocks.map((block) => block.id);
      setSelectedMemoryBlocks(allBlockIds);
    } else {
      setSelectedMemoryBlocks([]);
    }
  };

  const handleActionChange = async (e: React.ChangeEvent<HTMLSelectElement>, id: string): Promise<void> => {
    const selectedAction = e.target.value;
    e.target.value = ""; 

    if (selectedAction === 'view_edit') {
      navigate(`/memory-blocks/${id}`);
    } else if (selectedAction === 'hard_delete') { // New action for hard delete
      if (window.confirm('Are you sure you want to PERMANENTLY delete this archived memory block? This action cannot be undone.')) {
        try {
          await memoryService.deleteMemoryBlock(id); // Use the hard delete endpoint
          fetchArchivedMemoryBlocks(); // Refresh the list after deletion
        } catch (err: unknown) {
          const errorMessage = err instanceof Error ? err.message : 'Unknown error';
          setError('Failed to hard delete memory block: ' + errorMessage);
        }
      }
    } else if (selectedAction === 'unarchive') { // New action to unarchive
      if (window.confirm('Are you sure you want to unarchive this memory block? It will reappear in the main Memory Blocks list.')) {
        try {
          // Assuming an unarchive endpoint or update endpoint that sets archived to false
          await memoryService.updateMemoryBlock(id, { archived: false } as any); 
          fetchArchivedMemoryBlocks(); // Refresh the list after unarchiving
        } catch (err: unknown) {
          const errorMessage = err instanceof Error ? err.message : 'Unknown error';
          setError('Failed to unarchive memory block: ' + errorMessage);
        }
      }
    }
  };

  // Wrapper functions for child component compatibility
  const handleTableActionChange = (e: { target: { value: string } }, id: string): void => {
    // Convert the simple event object to a proper React.ChangeEvent
    const syntheticEvent = {
      target: { value: e.target.value }
    } as React.ChangeEvent<HTMLSelectElement>;
    handleActionChange(syntheticEvent, id);
  };

  const handleTableKeywordClick = (keyword: string): void => {
    // Convert single keyword click to array format for our handler
    handleKeywordChange([keyword]);
  };

  const resetFilters = () => {
    setSearchTerm('');
    setAgentIdInput('');
    setFilters({
      search_query: '',
      agent_id: '',
      conversation_id: '',
      feedback_score_range: [0, 100],
      retrieval_count_range: [0, 1000],
      start_date: '',
      end_date: '',
      keywords: [],
      search_type: 'fulltext',
      min_score: '',
      similarity_threshold: '',
      fulltext_weight: '',
      semantic_weight: '',
      min_combined_score: '',
    });
  };

  const areFiltersActive = () => {
    return Object.entries(filters).some(([key, value]) => {
      if (Array.isArray(value)) {
        if (key === 'feedback_score_range') return value[0] !== 0 || value[1] !== 100;
        if (key === 'retrieval_count_range') return value[0] !== 0 || value[1] !== 1000;
        return value.length > 0;
      }
      return value !== '';
    });
  };

  if (loading) return <p className="loading-message">Loading archived memory blocks...</p>;
  if (error) return <p className="error-message">Error: {error}</p>;

  if (featureDisabled) {
    return (
      <div className="p-6">
        <div className="max-w-3xl mx-auto text-center bg-gray-100 border border-dashed border-gray-300 rounded-xl p-10 text-gray-500">
          <h2 className="text-xl font-semibold text-gray-600 mb-2">Archived Memories</h2>
          <p className="text-sm text-gray-500">Feature coming soon.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="memory-block-list-container">
      {/* Empty State Message */}
      {!loading && !error && memoryBlocks.length === 0 && !areFiltersActive() && (
        <div className="empty-state-message">
          <p>No Archived Memory Blocks Found</p>
          <p>
            There are no memory blocks currently archived.
          </p>
        </div>
      )}

      {/* Empty State Message when filters are active but no results */}
      {!loading && !error && memoryBlocks.length === 0 && areFiltersActive() && (
        <div className="empty-state-message">
          <p>No Archived Memory Blocks Match Your Filters</p>
          <p>
            We couldn't find any archived memory blocks that match your current search criteria.
            Try adjusting your filters or clearing them.
          </p>
          <button onClick={resetFilters}>
            Clear Active Filters
          </button>
        </div>
      )}

      {(!loading && !error && (memoryBlocks.length > 0 || areFiltersActive())) && (
        <div>
          <MemoryBlockFilterBar
            filters={filters}
            searchTerm={searchTerm}
            agentIdInput={agentIdInput}
            onFilterChange={handleFilterChange}
            onRangeFilterChange={handleRangeFilterChange}
            onKeywordChange={handleKeywordChange}
            onAgentIdApply={handleAgentIdApply}
            availableKeywords={availableKeywords}
            availableAgentIds={availableAgentIds}
            showFilters={showFilters}
            toggleFilters={toggleFilters}
            resetFilters={resetFilters}
            areFiltersActive={areFiltersActive}
            // Advanced search props (placeholders for archived view)
            onAdvancedFilterChange={() => {}}
            showAdvancedSearch={false}
            toggleAdvancedSearch={() => {}}
          />

          {/* No BulkActionBar for archived blocks */}

          <MemoryBlockTable
            memoryBlocks={memoryBlocks}
            selectedMemoryBlocks={selectedMemoryBlocks}
            onSelectMemoryBlock={handleSelectMemoryBlock}
            onSelectAllMemoryBlocks={handleSelectAllMemoryBlocks}
            sort={sort}
            onSortChange={handleSortChange}
            onActionChange={handleTableActionChange}
            onKeywordClick={handleTableKeywordClick}
            navigate={navigate}
            isArchivedView={true} // Pass a prop to indicate archived view
          />

          <PaginationControls
            pagination={pagination}
            onPageChange={handlePageChange}
            onPerPageChange={handlePerPageChange}
            onPageInputChange={handlePageInputChange}
            pageInputValue={pageInputValue}
            onPageInputKeyPress={handlePageInputKeyPress}
            onPageInputBlur={handlePageInputBlur}
          />
        </div>
      )}
    </div>
  );
};

export default ArchivedMemoryBlockList;
