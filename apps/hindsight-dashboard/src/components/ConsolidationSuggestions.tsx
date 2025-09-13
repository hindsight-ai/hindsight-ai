import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getConsolidationSuggestions, validateConsolidationSuggestion, rejectConsolidationSuggestion, triggerConsolidation, deleteConsolidationSuggestion, ConsolidationSuggestion } from '../api/memoryService';
import notificationService from '../services/notificationService';
import StatCard from './StatCard';
import ConsolidationSuggestionModal from './ConsolidationSuggestionModal';

interface PaginationState {
  page: number;
  per_page: number;
  total_items: number;
  total_pages: number;
}

interface FiltersToSend {
  skip: number;
  limit: number;
  sort_by: string;
  sort_order: string;
  status?: string;
  search?: string;
}

const ConsolidationSuggestions: React.FC = () => {
  const [suggestions, setSuggestions] = useState<ConsolidationSuggestion[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [selectedSuggestionIds, setSelectedSuggestionIds] = useState<string[]>([]);
  const [showDetailModal, setShowDetailModal] = useState<boolean>(false);
  const [selectedSuggestionId, setSelectedSuggestionId] = useState<string | null>(null);

  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    per_page: 12, // More items per page for card layout
    total_items: 0,
    total_pages: 0,
  });

  const fetchSuggestions = useCallback(async (signal: AbortSignal, isMounted = true): Promise<void> => {
    if (isMounted) setLoading(true);
    if (isMounted) setError(null);
    try {
      const skip = (pagination.page - 1) * pagination.per_page;
      const filtersToSend: FiltersToSend = {
        skip: skip,
        limit: pagination.per_page,
        sort_by: 'timestamp',
        sort_order: 'desc',
        status: filterStatus === 'all' ? undefined : filterStatus,
      };

      if (searchTerm) {
        filtersToSend.search = searchTerm;
      }

      console.log('Fetching suggestions with filters:', filtersToSend);
      const response = await getConsolidationSuggestions(filtersToSend, signal);

      if (!signal.aborted && isMounted) {
        setSuggestions(response.items || []);
        setPagination((prevPagination) => ({
          ...prevPagination,
          total_items: response.total_items || 0,
          total_pages: response.total_pages || 0,
        }));
        setSelectedSuggestionIds([]);
        setLastUpdated(new Date());
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('Fetch aborted');
      } else if (isMounted) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        setError('Failed to load consolidation suggestions. Please check if the backend server is running or try again later. Error: ' + errorMessage);
        console.error(err);
      }
    } finally {
      if (!signal.aborted && isMounted) {
        setLoading(false);
      }
    }
  }, [pagination.page, pagination.per_page, filterStatus, searchTerm]);

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

  // Refresh when organization scope changes globally
  useEffect(() => {
    const handler = () => {
      const abortController = new AbortController();
      fetchSuggestions(abortController.signal);
    };
    window.addEventListener('orgScopeChanged', handler);
    return () => window.removeEventListener('orgScopeChanged', handler);
  }, [fetchSuggestions]);

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>): void => {
    if (event.target.checked) {
      const allSuggestionIds = suggestions.map(s => s.suggestion_id);
      setSelectedSuggestionIds(allSuggestionIds);
    } else {
      setSelectedSuggestionIds([]);
    }
  };

  const handleSelectItem = (event: React.ChangeEvent<HTMLInputElement>, suggestionId: string): void => {
    if (event.target.checked) {
      setSelectedSuggestionIds((prevSelected) => [...prevSelected, suggestionId]);
    } else {
      setSelectedSuggestionIds((prevSelected) =>
        prevSelected.filter((id) => id !== suggestionId)
      );
    }
  };

  const handleDeleteSelected = async (): Promise<void> => {
    if (window.confirm(`Are you sure you want to delete ${selectedSuggestionIds.length} selected suggestions?`)) {
      setLoading(true);
      try {
        await Promise.all(selectedSuggestionIds.map(id => deleteConsolidationSuggestion(id)));
        alert('Selected consolidation suggestions deleted successfully.');
        // Reset pagination to trigger a re-fetch via useEffect
        setPagination(prev => ({ ...prev, page: 1 }));
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        alert(`Failed to delete selected suggestions. Error: ${errorMessage}`);
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
  };

  const handlePageChange = (newPage: number): void => {
    if (newPage >= 1 && newPage <= pagination.total_pages) {
      setPagination((prevPagination) => ({
        ...prevPagination,
        page: newPage,
      }));
    }
  };

  const refreshData = (): void => {
    const abortController = new AbortController();
    fetchSuggestions(abortController.signal);
  };

  const handleValidate = async (suggestionId: string): Promise<void> => {
    try {
      const updatedSuggestion = await validateConsolidationSuggestion(suggestionId);
      alert(`Suggestion ${suggestionId.toString().slice(0, 8)}... validated successfully.`);
      // Update the suggestion status in the list
      setSuggestions(suggestions.map(suggestion => 
        suggestion.suggestion_id === suggestionId ? { ...suggestion, status: updatedSuggestion.status } : suggestion
      ));
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to validate suggestion ${suggestionId.toString().slice(0, 8)}.... Error: ${errorMessage}`);
      console.error(err);
    }
  };

  const handleReject = async (suggestionId: string): Promise<void> => {
    try {
      const updatedSuggestion = await rejectConsolidationSuggestion(suggestionId);
      alert(`Suggestion ${suggestionId.toString().slice(0, 8)}... rejected successfully.`);
      // Update the suggestion status in the list
      setSuggestions(suggestions.map(suggestion => 
        suggestion.suggestion_id === suggestionId ? { ...suggestion, status: updatedSuggestion.status } : suggestion
      ));
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to reject suggestion ${suggestionId.toString().slice(0, 8)}.... Error: ${errorMessage}`);
      console.error(err);
    }
  };

  const navigate = useNavigate();

  const handleTriggerConsolidation = async (): Promise<void> => {
    try {
      await triggerConsolidation();
      alert('Consolidation process triggered successfully.');
      // Reset pagination to trigger a re-fetch via useEffect
      setPagination(prev => ({ ...prev, page: 1 }));
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to trigger consolidation process. Error: ${errorMessage}`);
      console.error(err);
    }
  };

  const areFiltersActive = (): boolean => {
    return filterStatus !== 'all';
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'validated':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'rejected':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status: string): string => {
    switch (status) {
      case 'pending':
        return '⏳';
      case 'validated':
        return '✅';
      case 'rejected':
        return '❌';
      default:
        return '❓';
    }
  };

  const handleViewDetails = (suggestion: ConsolidationSuggestion): void => {
    setSelectedSuggestionId(suggestion.suggestion_id);
    setShowDetailModal(true);
  };

  const handleCloseModal = (): void => {
    setShowDetailModal(false);
    setSelectedSuggestionId(null);
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

      {/* Suggestions Grid */}
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
            <h3 className="text-lg font-medium text-red-800 mb-2">Error Loading Suggestions</h3>
            <p className="text-red-700 mb-4">{error}</p>
            <button
              onClick={() => refreshData()}
              className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      ) : suggestions.length === 0 ? (
        <div className="text-center py-12">
          <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {searchTerm || filterStatus !== 'all' ? 'No Suggestions Match Your Criteria' : 'No Consolidation Suggestions'}
          </h3>
          <p className="text-gray-500 mb-6">
            {searchTerm || filterStatus !== 'all'
              ? 'Try adjusting your search or filters to see more suggestions.'
              : 'Consolidation suggestions will appear here once the AI identifies opportunities to merge similar memories.'
            }
          </p>
          {searchTerm || filterStatus !== 'all' ? (
            <button
              onClick={() => {
                setSearchTerm('');
                setFilterStatus('all');
              }}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Clear Filters
            </button>
          ) : (
            <button
              onClick={handleTriggerConsolidation}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Trigger Consolidation
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {suggestions.map((suggestion) => (
              <div
                key={suggestion.suggestion_id}
                className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all duration-200 cursor-pointer"
                onClick={() => handleViewDetails(suggestion)}
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-start gap-4 flex-1">
                    <div className="bg-blue-100 p-3 rounded-lg flex-shrink-0">
                      <svg className="w-6 h-6 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-gray-500">ID: {suggestion.suggestion_id.toString().slice(0, 8)}...</span>
                        <span className={`text-xs px-2 py-1 rounded-full border ${getStatusColor(suggestion.status)}`}>
                          {getStatusIcon(suggestion.status)} {suggestion.status}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500">Group: {suggestion.group_id ? suggestion.group_id.toString().slice(0, 8) : 'N/A'}...</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 ml-2">
                    <input
                      type="checkbox"
                      checked={selectedSuggestionIds.includes(suggestion.suggestion_id)}
                      onChange={(e) => {
                        e.stopPropagation();
                        if (e.target.checked) {
                          setSelectedSuggestionIds(prev => [...prev, suggestion.suggestion_id]);
                        } else {
                          setSelectedSuggestionIds(prev => prev.filter(id => id !== suggestion.suggestion_id));
                        }
                      }}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div className="mb-4">
                  <h3 className="text-sm font-medium text-gray-800 mb-2">Suggested Content</h3>
                  <p className="text-sm text-gray-700 line-clamp-3">
                    {suggestion.suggested_content}
                  </p>
                </div>

                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4M4 7s-.5 1 .5 2M20 7s.5 1-.5 2m-19 5s.5-1-.5-2m19 5s-.5-1 .5-2" />
                    </svg>
                    <span className="text-sm text-gray-600">
                      {suggestion.original_memory_ids?.length || 0} original memories
                    </span>
                  </div>
                </div>

                <div className="flex gap-2">
                  {suggestion.status === 'pending' && (
                    <>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleValidate(suggestion.suggestion_id);
                        }}
                        className="flex-1 bg-green-600 text-white px-3 py-2 rounded-lg hover:bg-green-700 transition-colors text-sm font-medium"
                      >
                        Accept
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleReject(suggestion.suggestion_id);
                        }}
                        className="flex-1 bg-red-600 text-white px-3 py-2 rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
                      >
                        Reject
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {pagination.total_pages > 1 && (
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                Showing {((pagination.page - 1) * pagination.per_page) + 1} to {Math.min(pagination.page * pagination.per_page, pagination.total_items)} of {pagination.total_items} suggestions
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

      {/* Consolidation Suggestion Modal */}
      {showDetailModal && selectedSuggestionId && (
        <ConsolidationSuggestionModal
          isOpen={showDetailModal}
          onClose={handleCloseModal}
          suggestionId={selectedSuggestionId}
        />
      )}
    </div>
  );
};

export default ConsolidationSuggestions;
