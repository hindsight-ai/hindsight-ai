import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import memoryService from '../api/memoryService';
import MemoryBlockFilterBar from './MemoryBlockFilterBar';
import MemoryBlockTable from './MemoryBlockTable';
import PaginationControls from './PaginationControls';
import './MemoryBlockList.css'; // Reuse styles from MemoryBlockList

const ArchivedMemoryBlockList = () => {
  const [memoryBlocks, setMemoryBlocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState({
    search: '',
    agent_id: '',
    conversation_id: '',
    feedback_score_range: [0, 100],
    retrieval_count_range: [0, 1000],
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
  const [selectedMemoryBlocks, setSelectedMemoryBlocks] = useState([]); // Keep for consistency, but bulk actions won't be used
  const [showFilters, setShowFilters] = useState(true);

  const debounceTimeoutRef = useRef(null);

  const fetchArchivedMemoryBlocks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await memoryService.getArchivedMemoryBlocks({
        ...filters,
        min_feedback_score: filters.feedback_score_range[0],
        max_feedback_score: filters.feedback_score_range[1],
        min_retrieval_count: filters.retrieval_count_range[0],
        max_retrieval_count: filters.retrieval_count_range[1],
        page: pagination.page,
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
    } catch (err) {
      setError('Failed to fetch archived memory blocks: ' + err.message);
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.page, pagination.per_page, sort]);

  const fetchKeywords = useCallback(async () => {
    try {
      const response = await memoryService.getKeywords();
      setAvailableKeywords(response);
    } catch (err) {
      console.error('Failed to fetch keywords:', err);
    }
  }, []);

  useEffect(() => {
    setSelectedMemoryBlocks([]);
  }, [memoryBlocks]);

  const location = useLocation();

  useEffect(() => {
    setMemoryBlocks([]);
    setLoading(true);
    fetchArchivedMemoryBlocks();
    fetchKeywords();
  }, [filters, pagination.page, pagination.per_page, sort, location.pathname, fetchArchivedMemoryBlocks, fetchKeywords]);

  useEffect(() => {
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }

    debounceTimeoutRef.current = setTimeout(() => {
      setFilters((prevFilters) => ({
        ...prevFilters,
        search: searchTerm,
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

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    if (name === 'search') {
      setSearchTerm(value);
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
      page: 1,
    }));
    fetchArchivedMemoryBlocks();
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
    e.target.value = ""; 

    if (selectedAction === 'view_edit') {
      navigate(`/memory-blocks/${id}`);
    } else if (selectedAction === 'hard_delete') { // New action for hard delete
      if (window.confirm('Are you sure you want to PERMANENTLY delete this archived memory block? This action cannot be undone.')) {
        try {
          await memoryService.deleteMemoryBlock(id); // Use the hard delete endpoint
          fetchArchivedMemoryBlocks(); // Refresh the list after deletion
        } catch (err) {
          setError('Failed to hard delete memory block: ' + err.message);
        }
      }
    } else if (selectedAction === 'unarchive') { // New action to unarchive
      if (window.confirm('Are you sure you want to unarchive this memory block? It will reappear in the main Memory Blocks list.')) {
        try {
          // Assuming an unarchive endpoint or update endpoint that sets archived to false
          await memoryService.updateMemoryBlock(id, { archived: false }); 
          fetchArchivedMemoryBlocks(); // Refresh the list after unarchiving
        } catch (err) {
          setError('Failed to unarchive memory block: ' + err.message);
        }
      }
    }
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
          <button onClick={() => setFilters({
            search: '', agent_id: '', conversation_id: '', feedback_score_range: [0, 100],
            retrieval_count_range: [0, 1000], start_date: '', end_date: '', keywords: [],
          })}>
            Clear Active Filters
          </button>
        </div>
      )}

      {(!loading && !error && (memoryBlocks.length > 0 || areFiltersActive())) && (
        <div>
          <MemoryBlockFilterBar
            filters={filters}
            searchTerm={searchTerm}
            onFilterChange={handleFilterChange}
            onRangeFilterChange={handleRangeFilterChange}
            onKeywordChange={handleKeywordChange}
            availableKeywords={availableKeywords}
            showFilters={showFilters}
            toggleFilters={toggleFilters}
            resetFilters={() => setFilters({
              search: '', agent_id: '', conversation_id: '', feedback_score_range: [0, 100],
              retrieval_count_range: [0, 1000], start_date: '', end_date: '', keywords: [],
            })}
            areFiltersActive={areFiltersActive}
          />

          {/* No BulkActionBar for archived blocks */}

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
            isArchivedView={true} // Pass a prop to indicate archived view
          />

          <PaginationControls
            pagination={pagination}
            onPageChange={handlePageChange}
            onPerPageChange={handlePerPageChange}
            onPageInputChange={handlePageInputChange}
            fetchMemoryBlocks={fetchArchivedMemoryBlocks}
          />
        </div>
      )}
    </div>
  );
};

export default ArchivedMemoryBlockList;
