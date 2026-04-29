import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getConsolidationSuggestions, validateConsolidationSuggestion, rejectConsolidationSuggestion, triggerConsolidation, deleteConsolidationSuggestion, ConsolidationSuggestion } from '../api/memoryService';
import notificationService from '../services/notificationService';
import ConsolidationSuggestionModal from './ConsolidationSuggestionModal';
import { useAuth } from '../context/AuthContext';
import RefreshIndicator from './RefreshIndicator';
import usePageHeader from '../hooks/usePageHeader';
import Button from './Button';

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
  const { features } = useAuth();
  const llmDisabled = !features.llmEnabled;
  const featureDisabled = !features.consolidationEnabled;
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
    if (featureDisabled) {
      if (isMounted) {
        setSuggestions([]);
        setLoading(false);
        setError(null);
      }
      return;
    }
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
  }, [pagination.page, pagination.per_page, filterStatus, searchTerm, featureDisabled]);

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

  useEffect(() => {
    if (featureDisabled) {
      setSuggestions([]);
      setSelectedSuggestionIds([]);
      setLastUpdated(null);
      setLoading(false);
    }
  }, [featureDisabled]);

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
    if (llmDisabled) {
      notificationService.showInfo('LLM features are currently disabled.');
      return;
    }
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

  const handleRefresh = useCallback((): void => {
    const abortController = new AbortController();
    fetchSuggestions(abortController.signal);
  }, [fetchSuggestions]);

  const { setHeaderContent, clearHeaderContent } = usePageHeader();

  useEffect(() => {
    setHeaderContent({
      description: 'Review, validate, and manage consolidation suggestions generated by your AI agents.',
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

  const handleViewDetails = (suggestion: ConsolidationSuggestion): void => {
    setSelectedSuggestionId(suggestion.suggestion_id);
    setShowDetailModal(true);
  };

  const handleCloseModal = (): void => {
    setShowDetailModal(false);
    setSelectedSuggestionId(null);
  };

  if (featureDisabled) {
    return (
      <div className="p-6">
        <div className="max-w-3xl mx-auto text-center bg-gray-100 border border-dashed border-gray-300 rounded-xl p-10 text-gray-500">
          <h2 className="text-xl font-semibold text-gray-600 mb-2">Consolidation</h2>
          <p className="text-sm text-gray-500">Feature coming soon.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <p className="px-6 py-4 text-sm text-gray-500" data-testid="loading-message">
        Loading consolidation suggestions...
      </p>
    );
  }
  if (error) {
    return (
      <p
        className="mx-6 my-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        data-testid="error-message"
      >
        Error: {error}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-6">
      {/* Toolbar: bulk-delete + trigger + status filter. Always rendered. */}
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="secondary"
          onClick={handleDeleteSelected}
          disabled={selectedSuggestionIds.length === 0}
        >
          Delete Selected ({selectedSuggestionIds.length})
        </Button>
        <Button
          onClick={handleTriggerConsolidation}
          disabled={llmDisabled}
          title={llmDisabled ? 'LLM features are currently disabled' : undefined}
        >
          Trigger Consolidation
        </Button>
        <div className="ml-auto flex items-center gap-2">
          <label htmlFor="status-filter" className="text-sm font-medium text-gray-700">
            Filter by Status:
          </label>
          <select
            id="status-filter"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
          >
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="validated">Validated</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      {suggestions.length === 0 ? (
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
              className={`bg-blue-600 text-white px-6 py-2 rounded-lg transition-colors ${llmDisabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-700'}`}
              disabled={llmDisabled}
              title={llmDisabled ? 'LLM features are currently disabled' : undefined}
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
