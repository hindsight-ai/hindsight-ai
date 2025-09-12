// Refactored MemoryBlockList component
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { BulkActionBar } from './BulkActionBar';
import { useNavigate, useLocation } from 'react-router-dom'; // Import useLocation
import memoryService from '../api/memoryService';
import agentService from '../api/agentService'; // Import agentService
import notificationService from '../services/notificationService'; // Import notification service
import MemoryBlockFilterBar from './MemoryBlockFilterBar';
import MemoryBlockTable from './MemoryBlockTable';
import PaginationControls from './PaginationControls';
import { UIMemoryBlock, UIMemoryKeyword } from '../types/domain';
import { Agent } from '../api/agentService';

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

const MemoryBlockList = () => {
  const [memoryBlocks, setMemoryBlocks] = useState<UIMemoryBlock[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>(''); // Separate state for the search input value
  const [agentIdInput, setAgentIdInput] = useState<string>(''); // Local state for agent ID input
  const [filters, setFilters] = useState<FiltersState>({
    search_query: '', // This will be updated by the debounced searchTerm
    agent_id: '', // This will be updated only on explicit apply/enter
    conversation_id: '',
    feedback_score_range: [0, 100], // Default range for feedback score
    retrieval_count_range: [0, 1000], // Default range for retrieval count
    start_date: '',
    end_date: '',
    keywords: [],
    // Advanced search parameters
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
  const [pageInputValue, setPageInputValue] = useState<string>('1'); // Separate state for page input
  const [sort, setSort] = useState<SortState>({
    field: 'created_at',
    order: 'desc',
  });
  const [availableKeywords, setAvailableKeywords] = useState<UIMemoryKeyword[]>([]);
  const [selectedMemoryBlocks, setSelectedMemoryBlocks] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState<boolean>(true); // State for toggling filter visibility - always visible for better UX
  const [availableAgentIds, setAvailableAgentIds] = useState<string[]>([]); // New state for agent IDs
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null); // Track when data was last updated
  const [showAdvancedSearch, setShowAdvancedSearch] = useState<boolean>(false); // State for advanced search toggle

  // Debounce logic for search term
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Memoize fetch functions to ensure stable references for useEffect dependencies
  const fetchMemoryBlocks = useCallback(async () => {
    setLoading(true);
    setError(null); // Clear previous errors
    console.log('fetchMemoryBlocks called with filters.agent_id:', filters.agent_id); // Debugging line
    try {
      // Convert page-based pagination to offset-based pagination for backend API
      const skip = (pagination.page - 1) * pagination.per_page;
      const response = await memoryService.getMemoryBlocks({
        ...filters,
        min_feedback_score: filters.feedback_score_range[0],
        max_feedback_score: filters.feedback_score_range[1],
        min_retrieval_count: filters.retrieval_count_range[0],
        max_retrieval_count: filters.retrieval_count_range[1],
        skip: skip,
        per_page: pagination.per_page,
        sort_by: sort.field,
        sort_order: sort.order,
        keywords: filters.keywords.join(','), // Convert array to comma-separated string
        include_archived: false, // Filter out archived blocks by default
      });
      // Ensure response.items is an array before setting memory blocks
      if (response && Array.isArray(response.items)) {
        setMemoryBlocks(response.items);
      } else {
        setMemoryBlocks([]); // Default to empty array if items is not found or not an array
      }
      setPagination((prevPagination) => ({
        ...prevPagination,
        total_items: response.total_items,
        total_pages: response.total_pages,
      }));
      // Update last updated timestamp
      setLastUpdated(new Date());
    } catch (err: unknown) {
      // The memoryService will already show the 401 notification, so we just need to set the error for display
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError('Failed to fetch memory blocks: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.page, pagination.per_page, sort]); // Dependencies for useCallback

  const fetchKeywords = useCallback(async () => {
    try {
      const response = await memoryService.getKeywords();
      setAvailableKeywords(response);
    } catch (err) {
      console.error('Failed to fetch keywords:', err);
      // The memoryService will already show the 401 notification, so we don't need to do anything here
    }
  }, []);

  const fetchAgentIds = useCallback(async () => {
    try {
      const response = await agentService.getAgents({ per_page: 1000 }); // Fetch a reasonable number of agents
      // Ensure response.items is an array before mapping
      if (response && Array.isArray(response.items)) {
        setAvailableAgentIds(response.items.map((agent: Agent) => agent.agent_id));
      } else {
        setAvailableAgentIds([]); // Default to empty array if items is not found or not an array
      }
    } catch (err) {
      console.error('Failed to fetch agent IDs:', err);
      // The agentService will already show the 401 notification, so we don't need to do anything here
    }
  }, []);

  // Clear selections when page changes (but not when memoryBlocks change due to other reasons)
  useEffect(() => {
    setSelectedMemoryBlocks([]);
  }, [pagination.page]);

  // Keep pageInputValue in sync with pagination.page
  useEffect(() => {
    setPageInputValue(pagination.page.toString());
  }, [pagination.page]);

  // Effect to trigger fetch when filters (excluding search), pagination, or sort change
  const location = useLocation(); // Get location object
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

  // Listen for memory block added events
  useEffect(() => {
    const handleMemoryBlockAdded = () => {
      fetchMemoryBlocks(); // Refresh the list when a new memory block is added
    };

    window.addEventListener('memoryBlockAdded', handleMemoryBlockAdded);
    return () => window.removeEventListener('memoryBlockAdded', handleMemoryBlockAdded);
  }, []); // Remove fetchMemoryBlocks dependency to prevent unnecessary re-addition of listeners

  useEffect(() => {
    // Reset memory blocks and set loading state immediately on navigation/dependency change
    setMemoryBlocks([]);
    setLoading(true);
    fetchMemoryBlocks();
    fetchKeywords();
    fetchAgentIds(); // Fetch agent IDs
  }, [filters, pagination.page, pagination.per_page, sort, location.pathname, fetchKeywords, fetchAgentIds]); // Remove fetchMemoryBlocks from dependencies to prevent infinite loop

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

  // Effect to debounce search term and update filters.search_query
  useEffect(() => {
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }

    debounceTimeoutRef.current = setTimeout(() => {
      setFilters((prevFilters) => ({
        ...prevFilters,
        search_query: searchTerm,
      }));
    }, 500); // 500ms debounce delay

    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, [searchTerm]); // Only re-run if searchTerm changes

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
      setSearchTerm(value); // Update searchTerm for debouncing
    } else if (name === 'agent_id') {
      setAgentIdInput(value); // Update local agentIdInput state
      // No immediate filtering or validation for agent_id here.
      // Validation and filter application will happen on Enter key press via handleAgentIdApply.
    }
    else {
      setFilters((prevFilters) => ({
        ...prevFilters,
        [name]: value,
      }));
    }
  };

  const handleAgentIdApply = (agentId: string): void => {
    if (agentId === '' || isValidUUID(agentId)) {
      setFilters((prevFilters) => ({
        ...prevFilters,
        agent_id: agentId,
      }));
      setAgentIdInput(agentId); // Ensure agentIdInput reflects the applied filter
      if (agentId !== '') {
        notificationService.showInfo('Agent ID filter applied');
      }
    } else {
      notificationService.showWarning('Invalid Agent ID format. Please enter a valid UUID or select from suggestions.');
      setFilters((prevFilters) => ({
        ...prevFilters,
        agent_id: '', // Clear filter to prevent 422 errors
      }));
      setAgentIdInput(''); // Clear agentIdInput on invalid input
    }
    // The useEffect with 'filters' dependency will handle triggering fetchMemoryBlocks.
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
    // For dropdowns, still apply immediately for better UX
    // No need to call fetchMemoryBlocks here, as the state change will trigger it via useEffect
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
      page: 1, // Reset to first page when per_page changes
    }));
    // The useEffect will handle triggering fetchMemoryBlocks when pagination state changes
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
    // Reset the select to "Actions" after selection
    e.target.value = "";

    if (selectedAction === 'view_edit') {
      navigate(`/memory-blocks/${id}`);
    } else if (selectedAction === 'archive') { // Changed action to 'archive'
      if (window.confirm('Are you sure you want to archive this memory block?')) {
        try {
          await memoryService.archiveMemoryBlock(id); // Use archiveMemoryBlock
          fetchMemoryBlocks(); // Refresh the list after archiving
          notificationService.showSuccess('Memory block archived successfully');
        } catch (err: unknown) {
          const errorMessage = err instanceof Error ? err.message : 'Unknown error';
          notificationService.showError('Failed to archive memory block: ' + errorMessage);
        }
      }
    }
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

  const handlePageInputBlur = (): void => {
    handlePageInputSubmit();
  };

  const handleBulkArchive = async (): Promise<void> => {
    if (window.confirm(`Are you sure you want to archive ${selectedMemoryBlocks.length} memory blocks?`)) {
      try {
        await Promise.all(selectedMemoryBlocks.map(id => memoryService.archiveMemoryBlock(id)));
        fetchMemoryBlocks();
        setSelectedMemoryBlocks([]);
        notificationService.showSuccess(`${selectedMemoryBlocks.length} memory blocks archived successfully`);
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        notificationService.showError('Failed to archive memory blocks: ' + errorMessage);
      }
    }
  };

  const handleBulkTag = (): void => {
    alert('Bulk Tag functionality coming soon!');
  };

  const handleBulkExport = (): void => {
    alert('Bulk Export functionality coming soon!');
  };

  const handleRefreshData = async (): Promise<void> => {
    try {
      await fetchMemoryBlocks();
      notificationService.showSuccess('Data refreshed successfully');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      notificationService.showError('Failed to refresh data: ' + errorMessage);
    }
  };

  const resetFilters = (): void => {
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

  const areFiltersActive = (): boolean => {
    return Object.entries(filters).some(([key, value]) => {
      if (Array.isArray(value)) {
        if (key === 'feedback_score_range') return value[0] !== 0 || value[1] !== 100;
        if (key === 'retrieval_count_range') return value[0] !== 0 || value[1] !== 1000;
        return value.length > 0;
      }
      if (key === 'search_type') return value !== 'fulltext';
      return value !== '';
    });
  };

  const handleAdvancedFilterChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>): void => {
    const { name, value } = e.target;
    setFilters((prevFilters) => ({
      ...prevFilters,
      [name]: value,
    }));
  };

  const toggleAdvancedSearch = (): void => {
    setShowAdvancedSearch(!showAdvancedSearch);
  };

  // Placeholder functions for missing props
  const handleApplyFilters = (): void => {
    // Placeholder - could implement explicit apply functionality
  };

  const handleSearchTypeChange = (searchType: string): void => {
    setFilters((prevFilters) => ({
      ...prevFilters,
      search_type: searchType,
    }));
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

  if (loading) return (
    <div className="loading-container" data-testid="loading-indicator">
      <div className="loading-spinner">Loading memory blocks...</div>
    </div>
  );

  // Display error message if there is one
  if (error) return (
    <div className="error-message" data-testid="error-message">
      <p>Error: {error}</p>
      <button
        className="error-dismiss-btn"
        data-testid="dismiss-error"
        onClick={() => setError(null)}
      >
        Dismiss
      </button>
    </div>
  );

  return (
    <div className="memory-block-list-container">
      {/* Success Message */}
      {successMessage && (
        <div className="success-message" data-testid="success-message">
          <p>{successMessage}</p>
        </div>
      )}

      {/* Empty State Message */}
      {!loading && !error && memoryBlocks.length === 0 && !areFiltersActive() && (
        <div className="empty-state-message">
          <p>No Memory Blocks Found</p>
          <p>
            It looks like there are no memory blocks in your system.
            Start by creating a new one!
          </p>
          {/* The "Add New Memory Block" button is now in App.js header */}
        </div>
      )}

      {/* Empty State Message when filters are active but no results */}
      {!loading && !error && memoryBlocks.length === 0 && areFiltersActive() && (
        <div className="empty-state-message">
          <p>No Memory Blocks Match Your Filters</p>
          <p>
            We couldn't find any memory blocks that match your current search criteria.
            Try adjusting your filters or clearing them to see all memory blocks.
          </p>
          <button onClick={resetFilters}>
            Clear Active Filters
          </button>
        </div>
      )}

      {/* Render content only if there are memory blocks or filters are active */}
      {(!loading && !error && (memoryBlocks.length > 0 || areFiltersActive())) && (
        <div> {/* Replaced React.Fragment with a div */}
          <MemoryBlockFilterBar
            filters={filters}
            searchTerm={searchTerm} // Pass searchTerm to the filter bar
            agentIdInput={agentIdInput} // Pass agentIdInput to the filter bar
            onFilterChange={handleFilterChange}
            onRangeFilterChange={handleRangeFilterChange}
            onKeywordChange={handleKeywordChange}
            onAgentIdApply={handleAgentIdApply} // Pass new handler
            availableKeywords={availableKeywords}
            availableAgentIds={availableAgentIds as any} // Pass available agent IDs
            showFilters={showFilters}
            toggleFilters={toggleFilters}
            resetFilters={resetFilters}
            areFiltersActive={areFiltersActive}
            onApplyFilters={handleApplyFilters}
            // Advanced search props
            onSearchTypeChange={handleSearchTypeChange}
            onAdvancedFilterChange={handleAdvancedFilterChange}
            showAdvancedSearch={showAdvancedSearch}
            toggleAdvancedSearch={toggleAdvancedSearch}
          />

          {selectedMemoryBlocks.length > 0 && (
            <div> {/* Added wrapper div */}
              <BulkActionBar
                selectedCount={selectedMemoryBlocks.length}
                onBulkRemove={handleBulkArchive}
                onBulkTag={handleBulkTag}
                onBulkExport={handleBulkExport}
              />
            </div>
          )}

          {/* Memory Blocks Header - positioned above the table */}
          <div className="memory-blocks-header" style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '16px 25px',
            borderBottom: '1px solid #e0e0e0',
            marginBottom: '0',
            marginLeft: 'var(--content-margin)',
            marginRight: 'var(--content-margin)',
            width: 'var(--content-max-width)',
            boxSizing: 'border-box',
            minWidth: '0' // Allow flex items to shrink below their content size
          }}>
            {/* Total Count - Left Side */}
            <div className="total-count" style={{
              fontSize: '0.9em',
              color: '#666',
              fontWeight: '500',
              flexShrink: 0, // Prevent shrinking
              whiteSpace: 'nowrap'
            }}>
              {pagination.total_items > 0 && (
                <span>
                  {pagination.total_items} memory block{pagination.total_items !== 1 ? 's' : ''} found
                </span>
              )}
            </div>

            {/* Last Updated and Refresh - Right Side */}
            <div className="header-actions" style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              flexShrink: 0, // Prevent shrinking
              marginLeft: 'auto' // Push to the right
            }}>
              {lastUpdated && (
                <div className="last-updated" style={{
                  fontSize: '0.85em',
                  color: '#666',
                  fontWeight: '500',
                  whiteSpace: 'nowrap'
                }}>
                  Last updated: {lastUpdated.toLocaleString()}
                </div>
              )}

              <button
                className="refresh-button"
                data-testid="refresh-data"
                onClick={handleRefreshData}
                disabled={loading}
                style={{
                  backgroundColor: '#007bff',
                  color: 'white',
                  border: 'none',
                  padding: '6px 12px',
                  borderRadius: '4px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  fontSize: '13px',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  opacity: loading ? 0.6 : 1,
                  transition: 'background-color 0.2s ease',
                  whiteSpace: 'nowrap',
                  flexShrink: 0
                }}
              >
                {loading ? (
                  <>
                    <span data-testid="loading-indicator" style={{
                      display: 'inline-block',
                      animation: 'spin 1s linear infinite'
                    }}>⟳</span>
                    Loading...
                  </>
                ) : (
                  <>
                    <span>🔄</span>
                    Refresh
                  </>
                )}
              </button>

              {/* Test buttons for feedback system - only show in development mode */}
              {import.meta.env.DEV && (
                <>
                  <button
                    className="test-save-button"
                    data-testid="save-button"
                    onClick={() => notificationService.showSuccess('Item saved successfully')}
                    style={{
                      backgroundColor: '#28a745',
                      color: 'white',
                      border: 'none',
                      padding: '6px 10px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '11px',
                      whiteSpace: 'nowrap',
                      flexShrink: 0
                    }}
                  >
                    Test Save
                  </button>

                  <button
                    className="test-invalid-button"
                    data-testid="invalid-action"
                    onClick={() => notificationService.showError('Invalid action performed')}
                    style={{
                      backgroundColor: '#dc3545',
                      color: 'white',
                      border: 'none',
                      padding: '6px 10px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '11px',
                      whiteSpace: 'nowrap',
                      flexShrink: 0
                    }}
                  >
                    Test Error
                  </button>
                </>
              )}
            </div>
          </div>

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
            searchType={filters.search_type}
            showSearchScores={filters.search_type !== 'basic' && searchTerm.length > 0}
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

export default MemoryBlockList;
