// Refactored MemoryBlockList component
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { BulkActionBar } from './BulkActionBar';
import { useNavigate, useLocation } from 'react-router-dom'; // Import useLocation
import memoryService from '../api/memoryService';
import MemoryBlockFilterBar from './MemoryBlockFilterBar';
import MemoryBlockTable from './MemoryBlockTable';
import PaginationControls from './PaginationControls';
import './MemoryBlockList.css'; // Import the new CSS file

const MemoryBlockList = () => {
  const [memoryBlocks, setMemoryBlocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState(''); // Separate state for the search input value
  const [filters, setFilters] = useState({
    search: '', // This will be updated by the debounced searchTerm
    agent_id: '',
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

  // Debounce logic for search term
  const debounceTimeoutRef = useRef(null);

  // Memoize fetch functions to ensure stable references for useEffect dependencies
  const fetchMemoryBlocks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await memoryService.getMemoryBlocks({
        ...filters,
        min_feedback_score: filters.feedback_score_range[0],
        max_feedback_score: filters.feedback_score_range[1],
        min_retrieval_count: filters.retrieval_count_range[0],
        max_retrieval_count: filters.retrieval_count_range[1],
        page: pagination.page,
        per_page: pagination.per_page,
        sort_by: sort.field,
        sort_order: sort.order,
        keywords: filters.keywords.join(','), // Convert array to comma-separated string
      });
      setMemoryBlocks(response.items);
      setPagination((prevPagination) => ({
        ...prevPagination,
        total_items: response.total_items,
        total_pages: response.total_pages,
      }));
    } catch (err) {
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
    }
  }, []); // No dependencies, as keywords are static

  useEffect(() => {
    // Clear selections when memory blocks change (e.g., after fetch or delete)
    setSelectedMemoryBlocks([]);
  }, [memoryBlocks]);

  // Effect to trigger fetch when filters (excluding search), pagination, or sort change
  const location = useLocation(); // Get location object

  useEffect(() => {
    // Reset memory blocks and set loading state immediately on navigation/dependency change
    setMemoryBlocks([]);
    setLoading(true);
    fetchMemoryBlocks();
    fetchKeywords();
  }, [filters, pagination.page, pagination.per_page, sort, location.pathname, fetchMemoryBlocks, fetchKeywords]); // Add location.pathname and memoized functions as dependencies

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

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    if (name === 'search') {
      setSearchTerm(value); // Update searchTerm for debouncing
    } else {
      setFilters((prevFilters) => ({
        ...prevFilters,
        [name]: value,
      }));
    }
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
    // For dropdowns, still apply immediately for better UX
    fetchMemoryBlocks();
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

  const navigate = useNavigate();

  const handleActionChange = async (e, id) => {
    const selectedAction = e.target.value;
    // Reset the select to "Actions" after selection
    e.target.value = ""; 

    if (selectedAction === 'view_edit') {
      navigate(`/memory-blocks/${id}`);
    } else if (selectedAction === 'remove') {
      if (window.confirm('Are you sure you want to delete this memory block?')) {
        try {
          await memoryService.deleteMemoryBlock(id);
          fetchMemoryBlocks(); // Refresh the list after deletion
        } catch (err) {
          setError('Failed to delete memory block: ' + err.message);
        }
      }
    }
  };

  const handleBulkRemove = async () => {
    if (window.confirm(`Are you sure you want to delete ${selectedMemoryBlocks.length} memory blocks?`)) {
      try {
        await Promise.all(selectedMemoryBlocks.map(id => memoryService.deleteMemoryBlock(id)));
        fetchMemoryBlocks(); // Refresh the list after deletion
        setSelectedMemoryBlocks([]); // Clear selection
      } catch (err) {
        setError('Failed to delete memory blocks: ' + err.message);
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
            onFilterChange={handleFilterChange}
            onRangeFilterChange={handleRangeFilterChange}
            onKeywordChange={handleKeywordChange}
            availableKeywords={availableKeywords}
            showFilters={showFilters}
            toggleFilters={toggleFilters}
            resetFilters={resetFilters}
            areFiltersActive={areFiltersActive}
          />

          {selectedMemoryBlocks.length > 0 && (
            <div> {/* Added wrapper div */}
              <BulkActionBar
                selectedCount={selectedMemoryBlocks.length}
                onBulkRemove={handleBulkRemove}
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
