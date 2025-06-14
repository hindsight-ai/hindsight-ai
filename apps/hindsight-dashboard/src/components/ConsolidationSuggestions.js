import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getConsolidationSuggestions, validateConsolidationSuggestion, rejectConsolidationSuggestion, triggerConsolidation, deleteConsolidationSuggestion } from '../api/memoryService';
import PaginationControls from './PaginationControls'; // Import PaginationControls
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels'; // Import PanelGroup and Panel
import './MemoryBlockList.css'; // Reuse styles from MemoryBlockList if applicable

const allColumnDefinitions = [
  { id: 'select', label: 'Select', size: 3, isResizable: false, minSize: 3, maxSize: 3 },
  { id: 'suggestion_id', label: 'ID', size: 10, isSortable: true },
  { id: 'group_id', label: 'Group ID', size: 10, isSortable: true },
  { id: 'suggested_content', label: 'Suggested Content', size: 50 },
  { id: 'original_memories', label: 'Original Memories', size: 10 },
  { id: 'status', label: 'Status', size: 7, isSortable: true },
  { id: 'actions', label: 'Actions', size: 10 },
];

const initialColumnLayout = allColumnDefinitions.map(col => col.size);

const ConsolidationSuggestions = () => {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 10,
    total_items: 0,
    total_pages: 0,
  });
  const [sort, setSort] = useState({
    field: 'timestamp',
    order: 'desc',
  });
  const [selectedSuggestionIds, setSelectedSuggestionIds] = useState([]); // New state for selected items
  const [filterStatus, setFilterStatus] = useState('all'); // New state for status filter
  const [, setColumnLayout] = useState(initialColumnLayout);

  // Reset column layout when component mounts
  useEffect(() => {
    setColumnLayout(initialColumnLayout);
  }, []);

  const fetchSuggestions = useCallback(async (signal, isMounted = true) => {
    if (isMounted) setLoading(true);
    if (isMounted) setError(null);
    try {
      const skip = (pagination.page - 1) * pagination.per_page;
      const filtersToSend = {
        skip: skip,
        limit: pagination.per_page,
        sort_by: sort.field,
        sort_order: sort.order,
        status: filterStatus === 'all' ? undefined : filterStatus,
      };
      console.log('Fetching suggestions with filters:', filtersToSend);
      const response = await getConsolidationSuggestions(filtersToSend, signal); // Pass signal to API call

      if (!signal.aborted && isMounted) { // Only update state if not aborted and mounted
        setSuggestions(response.items || []);
        setPagination((prevPagination) => ({
          ...prevPagination,
          total_items: response.total_items,
          total_pages: response.total_pages,
        }));
        setSelectedSuggestionIds([]);
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Fetch aborted');
      } else if (isMounted) {
        setError('Failed to load consolidation suggestions. Please check if the backend server is running or try again later. Error: ' + err.message);
        console.error(err);
      }
    } finally {
      if (!signal.aborted && isMounted) {
        setLoading(false);
      }
    }
  }, [pagination.page, pagination.per_page, sort, filterStatus]); // Dependencies for useCallback

  useEffect(() => {
    let isMounted = true;
    const abortController = new AbortController();
    const signal = abortController.signal;

    fetchSuggestions(signal, isMounted);

    return () => {
      isMounted = false;
      abortController.abort(); // Abort fetch request on unmount
    };
  }, [fetchSuggestions]); // Dependency for useEffect

  const handleSelectAll = (event) => {
    if (event.target.checked) {
      const allSuggestionIds = suggestions.map(s => s.suggestion_id);
      setSelectedSuggestionIds(allSuggestionIds);
    } else {
      setSelectedSuggestionIds([]);
    }
  };

  const handleSelectItem = (event, suggestionId) => {
    if (event.target.checked) {
      setSelectedSuggestionIds((prevSelected) => [...prevSelected, suggestionId]);
    } else {
      setSelectedSuggestionIds((prevSelected) =>
        prevSelected.filter((id) => id !== suggestionId)
      );
    }
  };

  const handleDeleteSelected = async () => {
    if (window.confirm(`Are you sure you want to delete ${selectedSuggestionIds.length} selected suggestions?`)) {
      setLoading(true);
      try {
        await Promise.all(selectedSuggestionIds.map(id => deleteConsolidationSuggestion(id)));
        alert('Selected consolidation suggestions deleted successfully.');
        // Reset pagination to trigger a re-fetch via useEffect
        setPagination(prev => ({ ...prev, page: 1 }));
      } catch (err) {
        alert(`Failed to delete selected suggestions. Error: ${err.message}`);
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
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
    // fetchSuggestions will be called by the useEffect due to pagination.per_page change
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

  const handleValidate = async (suggestionId) => {
    try {
      const updatedSuggestion = await validateConsolidationSuggestion(suggestionId);
      alert(`Suggestion ${suggestionId.toString().slice(0, 8)}... validated successfully.`);
      // Update the suggestion status in the list
      setSuggestions(suggestions.map(suggestion => 
        suggestion.suggestion_id === suggestionId ? { ...suggestion, status: updatedSuggestion.status } : suggestion
      ));
    } catch (err) {
      alert(`Failed to validate suggestion ${suggestionId.toString().slice(0, 8)}.... Error: ${err.message}`);
      console.error(err);
    }
  };

  const handleReject = async (suggestionId) => {
    try {
      const updatedSuggestion = await rejectConsolidationSuggestion(suggestionId);
      alert(`Suggestion ${suggestionId.toString().slice(0, 8)}... rejected successfully.`);
      // Update the suggestion status in the list
      setSuggestions(suggestions.map(suggestion => 
        suggestion.suggestion_id === suggestionId ? { ...suggestion, status: updatedSuggestion.status } : suggestion
      ));
    } catch (err) {
      alert(`Failed to reject suggestion ${suggestionId.toString().slice(0, 8)}.... Error: ${err.message}`);
      console.error(err);
    }
  };

  const navigate = useNavigate();

  const handleTriggerConsolidation = async () => {
    try {
      await triggerConsolidation();
      alert('Consolidation process triggered successfully.');
      // Reset pagination to trigger a re-fetch via useEffect
      setPagination(prev => ({ ...prev, page: 1 }));
    } catch (err) {
      alert(`Failed to trigger consolidation process. Error: ${err.message}`);
      console.error(err);
    }
  };

  const areFiltersActive = () => {
    return filterStatus !== 'all';
  };

  if (loading) return <p className="loading-message">Loading consolidation suggestions...</p>;
  if (error) return <p className="error-message">Error: {error}</p>;

  return (
    <div className="memory-block-list-container">
      {/* Filter Controls - Always render these */}
      <div className="bulk-actions-bar">
        <button
          onClick={handleDeleteSelected}
          disabled={selectedSuggestionIds.length === 0}
          className="delete-selected-button"
        >
          Delete Selected ({selectedSuggestionIds.length})
        </button>
        <button onClick={handleTriggerConsolidation} className="add-button">
          Trigger Consolidation
        </button>
        <div className="filter-controls">
          <label htmlFor="status-filter">Filter by Status:</label>
          <select
            id="status-filter"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="filter-select"
          >
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="validated">Validated</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      {/* Empty State Message when no filters are active and no results */}
      {!loading && !error && suggestions.length === 0 && !areFiltersActive() && (
        <div className="empty-state-message">
          <p>No Consolidation Suggestions Found</p>
          <p>
            It looks like there are no consolidation suggestions in your system at the moment.
            Try triggering the consolidation process manually if needed.
          </p>
          <button onClick={handleTriggerConsolidation} className="add-button">
            Trigger Consolidation
          </button>
        </div>
      )}

      {/* Empty State Message when filters are active but no results */}
      {!loading && !error && suggestions.length === 0 && areFiltersActive() && (
        <div className="empty-state-message">
          <p>No Consolidation Suggestions Match Your Criteria</p>
          <p>
            We couldn't find any consolidation suggestions that match your current criteria.
            Try adjusting your filters or clearing them to see all suggestions.
          </p>
          {/* No filters to clear yet, but keeping the structure for future */}
        </div>
      )}

      {/* Render table content only if there are suggestions */}
      {!loading && !error && suggestions.length > 0 && (
        <div className="memory-block-table-container">
          <div className="memory-block-table-header">
            <PanelGroup direction="horizontal" onLayout={setColumnLayout}>
              <Panel defaultSize={3} minSize={3} maxSize={3} style={{ padding: 0, margin: 0 }}>
                <div className="header-cell select-cell">
                  <input
                    type="checkbox"
                    onChange={handleSelectAll}
                    checked={selectedSuggestionIds.length === suggestions.length && suggestions.length > 0}
                  />
                </div>
              </Panel>
              <PanelResizeHandle className="resize-handle" />
              <Panel defaultSize={10} minSize={5} style={{ padding: 0, margin: 0 }}>
                <div className="header-cell sortable-header" onClick={() => handleSortChange('suggestion_id')}>
                  ID {sort.field === 'suggestion_id' && (sort.order === 'asc' ? '↑' : '↓')}
                </div>
              </Panel>
              <PanelResizeHandle className="resize-handle" />
              <Panel defaultSize={10} minSize={5} style={{ padding: 0, margin: 0 }}>
                <div className="header-cell sortable-header" onClick={() => handleSortChange('group_id')}>
                  Group ID {sort.field === 'group_id' && (sort.order === 'asc' ? '↑' : '↓')}
                </div>
              </Panel>
              <PanelResizeHandle className="resize-handle" />
              <Panel defaultSize={50} minSize={20} style={{ padding: 0, margin: 0 }}>
                <div className="header-cell">Suggested Content</div>
              </Panel>
              <PanelResizeHandle className="resize-handle" />
              <Panel defaultSize={10} minSize={5} style={{ padding: 0, margin: 0 }}>
                <div className="header-cell">Original Memories</div>
              </Panel>
              <PanelResizeHandle className="resize-handle" />
              <Panel defaultSize={7} minSize={5} style={{ padding: 0, margin: 0 }}>
                <div className="header-cell sortable-header" onClick={() => handleSortChange('status')}>
                  Status {sort.field === 'status' && (sort.order === 'asc' ? '↑' : '↓')}
                </div>
              </Panel>
              <PanelResizeHandle className="resize-handle" />
              <Panel defaultSize={10} minSize={5} style={{ padding: 0, margin: 0 }}>
                <div className="header-cell actions-cell">Actions</div>
              </Panel>
            </PanelGroup>
          </div>
          <div className="memory-block-table-body">
            {suggestions.map((suggestion, rowIndex) => (
              <div key={suggestion.suggestion_id} className="memory-block-table-row">
                <PanelGroup direction="horizontal" id={`row-panel-group-${rowIndex}`}>
                  <Panel defaultSize={3} minSize={3} maxSize={3} style={{ padding: 0, margin: 0 }}>
                    <div className="data-cell select-cell">
                      <input
                        type="checkbox"
                        checked={selectedSuggestionIds.includes(suggestion.suggestion_id)}
                        onChange={(event) => handleSelectItem(event, suggestion.suggestion_id)}
                      />
                    </div>
                  </Panel>
                  <PanelResizeHandle className="resize-handle" />
                  <Panel defaultSize={10} minSize={5} style={{ padding: 0, margin: 0 }}>
                    <div className="data-cell id-cell">{suggestion.suggestion_id.toString().slice(0, 8)}...</div>
                  </Panel>
                  <PanelResizeHandle className="resize-handle" />
                  <Panel defaultSize={10} minSize={5} style={{ padding: 0, margin: 0 }}>
                    <div className="data-cell id-cell">{suggestion.group_id.toString().slice(0, 8)}...</div>
                  </Panel>
                  <PanelResizeHandle className="resize-handle" />
                  <Panel defaultSize={50} minSize={20} style={{ padding: 0, margin: 0 }}>
                    <div className="data-cell lessons-learned-cell">{suggestion.suggested_content.slice(0, 150)}...</div>
                  </Panel>
                  <PanelResizeHandle className="resize-handle" />
                  <Panel defaultSize={10} minSize={5} style={{ padding: 0, margin: 0 }}>
                    <div className="data-cell">{suggestion.original_memory_ids.length} memories</div>
                  </Panel>
                  <PanelResizeHandle className="resize-handle" />
                  <Panel defaultSize={7} minSize={5} style={{ padding: 0, margin: 0 }}>
                    <div className="data-cell">{suggestion.status}</div>
                  </Panel>
                  <PanelResizeHandle className="resize-handle" />
                  <Panel defaultSize={10} minSize={5} style={{ padding: 0, margin: 0 }}>
                    <div className="data-cell actions-cell">
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        navigate(`/consolidation-suggestions/${suggestion.suggestion_id}`);
                      }}
                      className="action-icon-button view-edit-button"
                      title="View Details"
                    >
                      👁️
                    </button>
                    {suggestion.status === 'pending' && (
                      <>
                        <button onClick={() => handleValidate(suggestion.suggestion_id)} className="action-icon-button view-edit-button" title="Validate Suggestion">
                          ✔️
                        </button>
                        <button onClick={() => handleReject(suggestion.suggestion_id)} className="action-icon-button remove-button" title="Reject Suggestion">
                          ✖️
                        </button>
                      </>
                    )}
                    </div>
                  </Panel>
                </PanelGroup>
              </div>
            ))}
          </div>
          <PaginationControls
            pagination={pagination}
            onPageChange={handlePageChange}
            onPerPageChange={handlePerPageChange}
            onPageInputChange={handlePageInputChange}
          />
        </div>
      )}
    </div>
  );
};

export default ConsolidationSuggestions;
