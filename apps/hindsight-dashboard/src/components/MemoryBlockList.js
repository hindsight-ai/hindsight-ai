// Refactored MemoryBlockList component
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { BulkActionBar } from './BulkActionBar';
import { useNavigate, useLocation } from 'react-router-dom'; // Import useLocation
import memoryService from '../api/memoryService';
import agentService from '../api/agentService'; // Import agentService
import MemoryBlockFilterBar from './MemoryBlockFilterBar';
import MemoryBlockTable from './MemoryBlockTable';
import PaginationControls from './PaginationControls';
import './MemoryBlockList.css'; // Import the new CSS file

const MemoryBlockList = () => {
  const [memoryBlocks, setMemoryBlocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState(''); // Separate state for the search input value
  const [agentIdInput, setAgentIdInput] = useState(''); // Local state for agent ID input
  const [filters, setFilters] = useState({
    search: '', // This will be updated by the debounced searchTerm
    agent_id: '', // This will be updated only on explicit apply/enter
    conversation_id: '',
    feedback_score_range: [0, 100], // Default range for feedback score
    retrieval_count_range: [0, 1000], // Default range for retrieval count
    start_date: '',
    end_date: '',
    keywords: [],
  });

  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 10,
    total_items: 0,
    total_pages: 0,
  });
  const [sort, setSort] = useState({
    field: 'creation_date',
    order: 'desc',
  });
  const [availableKeywords, setAvailableKeywords] = useState([]);
  const [selectedMemoryBlocks, setSelectedMemoryBlocks] = useState([]);
  const [showFilters, setShowFilters] = useState(true); // State for toggling filter visibility
  const [availableAgentIds, setAvailableAgentIds] = useState([]); // New state for agent IDs

  // Debounce logic for search term
  const debounceTimeoutRef = useRef(null);

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
    } catch (err) {
      // The memoryService will already show the 401 notification, so we just need to set the error for display
      setError('Failed to fetch memory blocks: ' + err.message);
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
        setAvailableAgentIds(response.items.map(agent => agent.id));
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

  // Effect to trigger fetch when filters (excluding search), pagination, or sort change
  const location = useLocation(); // Get location object
  const navigate = useNavigate();

  // Initialize pagination state from URL parameters
  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);
    const pageFromUrl = parseInt(urlParams.get('page')) || 1;
    const perPageFromUrl = parseInt(urlParams.get('per_page')) || 10;

    setPagination((prevPagination) => ({
      ...prevPagination,
      page: pageFromUrl,
      per_page: perPageFromUrl,
    }));
  }, [location.search]);

  useEffect(() => {
    // Reset memory blocks and set loading state immediately on navigation/dependency change
    setMemoryBlocks([]);
    setLoading(true);
    fetchMemoryBlocks();
    fetchKeywords();
    fetchAgentIds(); // Fetch agent IDs
  }, [filters, pagination.page, pagination.per_page, sort, location.pathname, fetchMemoryBlocks, fetchKeywords, fetchAgentIds]); // Add location.pathname and memoized functions as dependencies

  // Update URL parameters when pagination state changes
  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);

    // Only update URL if pagination values are different from URL
    const currentPage = parseInt(urlParams.get('page')) || 1;
    const currentPerPage = parseInt(urlParams.get('per_page')) || 10;

    if (pagination.page !== currentPage || pagination.per_page !== currentPerPage) {
      urlParams.set('page', pagination.page.toString());
      urlParams.set('per_page', pagination.per_page.toString());

      // Preserve other existing parameters
      const newSearch = urlParams.toString();
      navigate(`${location.pathname}?${newSearch}`, { replace: true });
    }
  }, [pagination.page, pagination.per_page, location.pathname, location.search, navigate]);

  // Effect to debounce search term and update filters.search
  useEffect(() => {
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }

    debounceTimeoutRef.current = setTimeout(() => {
      setFilters((prevFilters) => ({
        ...prevFilters,
        search: searchTerm,
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
  const isValidUUID = (uuidString) => {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuidString);
  };

  const handleFilterChange = (e) => {
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

  const handleAgentIdApply = (agentId) => {
    if (agentId === '' || isValidUUID(agentId)) {
      setError(null); // Clear error if input is valid or empty
      setFilters((prevFilters) => ({
        ...prevFilters,
        agent_id: agentId,
      }));
      setAgentIdInput(agentId); // Ensure agentIdInput reflects the applied filter
    } else {
      setError('Invalid Agent ID format. Please enter a valid UUID or select from suggestions.');
      setFilters((prevFilters) => ({
        ...prevFilters,
        agent_id: '', // Clear filter to prevent 422 errors
      }));
      setAgentIdInput(''); // Clear agentIdInput on invalid input
    }
    // The useEffect with 'filters' dependency will handle triggering fetchMemoryBlocks.
  };

  const handleRangeFilterChange = (name, value) => {
    setFilters((prevFilters) => ({
      ...prevFilters,
      [name]: value,
    }));
  };

  const handleKeywordChange = (selectedKeywords) => {
    setFilters((prevFilters) => ({
      ...prevFilters,
      keywords: selectedKeywords,
    }));
    // For dropdowns, still apply immediately for better UX
    // No need to call fetchMemoryBlocks here, as the state change will trigger it via useEffect
  };

  const handleSortChange = (field) => {
    setSort((prevSort) => ({
      field,
      order: prevSort.field === field && prevSort.order === 'asc' ? 'desc' : 'asc',
    }));
  };

  const handlePerPageChange = (e) => {
    setPagination((prevPagination) => ({
      ...prevPagination,
      per_page: parseInt(e.target.value),
      page: 1, // Reset to first page when per_page changes
    }));
    // The useEffect will handle triggering fetchMemoryBlocks when pagination state changes
  };

  const handlePageChange = (newPage) => {
    const totalPages = pagination.total_pages;
    if (newPage >= 1 && newPage <= totalPages) {
      setPagination((prevPagination) => ({
        ...prevPagination,
        page: newPage,
      }));
    }
  };

  const handlePageInputChange = (e) => {
    const page = parseInt(e.target.value);
    if (!isNaN(page) && page >= 1 && page <= pagination.total_pages) {
      handlePageChange(page);
    }
  };

  const handleSelectMemoryBlock = (id) => {
    setSelectedMemoryBlocks((prevSelected) =>
      prevSelected.includes(id)
        ? prevSelected.filter((blockId) => blockId !== id)
        : [...prevSelected, id]
    );
  };

  const handleSelectAllMemoryBlocks = (e) => {
    if (e.target.checked) {
      const allBlockIds = memoryBlocks.map((block) => block.id);
      setSelectedMemoryBlocks(allBlockIds);
    } else {
      setSelectedMemoryBlocks([]);
    }
  };

  const handleActionChange = async (e, id) => {
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
        } catch (err) {
          setError('Failed to archive memory block: ' + err.message);
        }
      }
    }
  };

  const handleBulkArchive = async () => { // Renamed function to handleBulkArchive
    if (window.confirm(`Are you sure you want to archive ${selectedMemoryBlocks.length} memory blocks?`)) {
      try {
        await Promise.all(selectedMemoryBlocks.map(id => memoryService.archiveMemoryBlock(id))); // Use archiveMemoryBlock
        fetchMemoryBlocks(); // Refresh the list after archiving
        setSelectedMemoryBlocks([]); // Clear selection
      } catch (err) {
        setError('Failed to archive memory blocks: ' + err.message);
      }
    }
  };

  const handleBulkTag = () => {
    alert('Bulk Tag functionality coming soon!');
    // Placeholder for bulk tagging logic
  };

  const handleBulkExport = () => {
    alert('Bulk Export functionality coming soon!');
    // Placeholder for bulk export logic
  };

  const resetFilters = () => {
    setSearchTerm(''); // Reset search term
    setAgentIdInput(''); // Reset agent ID input
    setFilters({
      search: '',
      agent_id: '',
      conversation_id: '',
      feedback_score_range: [0, 100],
      retrieval_count_range: [0, 1000],
      start_date: '',
      end_date: '',
      keywords: [],
    });

    // No need to call fetchMemoryBlocks here, as the state change will trigger it via useEffect
  };

  // Function to check if any filter is active
  const areFiltersActive = () => {
    return Object.entries(filters).some(([key, value]) => {
      if (Array.isArray(value)) {
        // For range sliders, check if values are not at their default min/max
        if (key === 'feedback_score_range') return value[0] !== 0 || value[1] !== 100;
        if (key === 'retrieval_count_range') return value[0] !== 0 || value[1] !== 1000;
        return value.length > 0; // For other arrays like keywords
      }
      return value !== '';
    });
  };

  if (loading) return <p className="loading-message">Loading memory blocks...</p>;
  // Display error message if there is one
  if (error) return <p className="error-message">Error: {error}</p>;

  return (
    <div className="memory-block-list-container">
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
            availableAgentIds={availableAgentIds} // Pass available agent IDs
            showFilters={showFilters}
            toggleFilters={toggleFilters}
            resetFilters={resetFilters}
            areFiltersActive={areFiltersActive}
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

          <MemoryBlockTable
            memoryBlocks={memoryBlocks}
            selectedMemoryBlocks={selectedMemoryBlocks}
            onSelectMemoryBlock={handleSelectMemoryBlock}
            onSelectAllMemoryBlocks={handleSelectAllMemoryBlocks}
            sort={sort}
            onSortChange={handleSortChange}
            onActionChange={handleActionChange}
            onKeywordClick={handleKeywordChange}
            navigate={navigate}
          />

          <PaginationControls
            pagination={pagination}
            onPageChange={handlePageChange}
            onPerPageChange={handlePerPageChange}
            onPageInputChange={handlePageInputChange}
            fetchMemoryBlocks={fetchMemoryBlocks}
          />
        </div>
      )}
    </div>
  );
};

export default MemoryBlockList;
