import React, { useState, useEffect } from 'react';
import Portal from './Portal';
import memoryService, { Keyword } from '../api/memoryService';
import notificationService from '../services/notificationService';
import StatCard from './StatCard';
import { UIMemoryBlock } from '../types/domain';

interface ExtendedKeyword extends Keyword {
  created_at?: string;
}

interface KeywordUsageCounts {
  [keywordId: string]: number;
}

const KeywordManager: React.FC = () => {
  const [keywords, setKeywords] = useState<ExtendedKeyword[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [editingKeyword, setEditingKeyword] = useState<ExtendedKeyword | null>(null);
  const [newKeywordText, setNewKeywordText] = useState<string>('');
  const [showAssociationsModal, setShowAssociationsModal] = useState<boolean>(false);
  const [selectedKeyword, setSelectedKeyword] = useState<ExtendedKeyword | null>(null);
  const [associatedMemoryBlocks, setAssociatedMemoryBlocks] = useState<UIMemoryBlock[]>([]);
  const [loadingAssociations, setLoadingAssociations] = useState<boolean>(false);
  const [keywordUsageCounts, setKeywordUsageCounts] = useState<KeywordUsageCounts>({});

  useEffect(() => {
    fetchKeywords();
  }, []);

  useEffect(() => {
    if (keywords.length > 0) {
      fetchKeywordUsageCounts();
    }
  }, [keywords]);

  const fetchKeywords = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await memoryService.getKeywords();

      // Handle different response structures
      let keywordsData: ExtendedKeyword[] = [];
      if (Array.isArray(response)) {
        keywordsData = response;
      } else if (response && Array.isArray(response.items)) {
        keywordsData = response.items;
      } else if (response && typeof response === 'object') {
        // Try to extract keywords from various possible structures
        keywordsData = response.keywords || response.data || [];
      }

      setKeywords(keywordsData);
      setLastUpdated(new Date());
    } catch (err: unknown) {
      console.error('Error fetching keywords:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError('Failed to fetch keywords: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleAddKeyword = async (): Promise<void> => {
    if (!newKeywordText.trim()) return;

    try {
      await memoryService.createKeyword({ keyword_text: newKeywordText.trim() });
      setNewKeywordText('');
      setShowAddModal(false);
      fetchKeywords();
      notificationService.showSuccess('Keyword added successfully');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      notificationService.showError('Failed to add keyword: ' + errorMessage);
    }
  };

  const handleEditKeyword = async (keyword: ExtendedKeyword): Promise<void> => {
    if (!editingKeyword?.keyword_text?.trim()) return;

    try {
      await memoryService.updateKeyword(keyword.keyword_id, {
        keyword_text: editingKeyword.keyword_text.trim()
      });
      setEditingKeyword(null);
      fetchKeywords();
      notificationService.showSuccess('Keyword updated successfully');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      notificationService.showError('Failed to update keyword: ' + errorMessage);
    }
  };

  const handleDeleteKeyword = async (keywordId: string): Promise<void> => {
    if (window.confirm('Are you sure you want to delete this keyword?')) {
      try {
        await memoryService.deleteKeyword(keywordId);
        fetchKeywords();
        notificationService.showSuccess('Keyword deleted successfully');
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        notificationService.showError('Failed to delete keyword: ' + errorMessage);
      }
    }
  };

  const filteredKeywords = keywords.filter((keyword: ExtendedKeyword) =>
    keyword.keyword_text.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const fetchKeywordUsageCounts = async (): Promise<void> => {
    const counts: KeywordUsageCounts = {};
    for (const keyword of keywords) {
      try {
        const response = await memoryService.getKeywordMemoryBlocksCount(keyword.keyword_id);
        counts[keyword.keyword_id] = response.count || 0;
      } catch (err: unknown) {
        console.error(`Error fetching usage count for keyword ${keyword.keyword_id}:`, err);
        counts[keyword.keyword_id] = 0;
      }
    }
    setKeywordUsageCounts(counts);
  };

  const handleViewAssociations = async (keyword: ExtendedKeyword): Promise<void> => {
    setSelectedKeyword(keyword);
    setLoadingAssociations(true);
    setShowAssociationsModal(true);

    try {
      const memoryBlocks = await memoryService.getKeywordMemoryBlocks(keyword.keyword_id);
      setAssociatedMemoryBlocks(Array.isArray(memoryBlocks) ? memoryBlocks : []);
    } catch (err: unknown) {
      console.error('Error fetching associated memory blocks:', err);
      setAssociatedMemoryBlocks([]);
      notificationService.showError('Failed to load associated memory blocks');
    } finally {
      setLoadingAssociations(false);
    }
  };

  const handleCloseAssociationsModal = (): void => {
    setShowAssociationsModal(false);
    setSelectedKeyword(null);
    setAssociatedMemoryBlocks([]);
  };

  const keywordStats = {
    total: keywords.length,
    recent: keywords.filter((k: ExtendedKeyword) => {
      const createdDate = new Date(k.created_at || Date.now());
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      return createdDate > weekAgo;
    }).length
  };

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <svg className="w-6 h-6 text-blue-500 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
          </svg>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Keywords</h1>
            <p className="text-gray-600">Manage and organize your keyword tags</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-sm text-gray-500">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={fetchKeywords}
            disabled={loading}
            className="text-sm text-gray-600 hover:text-gray-800 flex items-center gap-1 disabled:opacity-50"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          title="Total Keywords"
          value={keywordStats.total}
          color="blue"
          loading={loading}
          error={!!error}
          icon={
            <svg className="w-6 h-6 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
            </svg>
          }
        />

        <StatCard
          title="Recent Keywords"
          value={keywordStats.recent}
          color="green"
          loading={loading}
          error={!!error}
          icon={
            <svg className="w-6 h-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />

        <StatCard
          title="Filtered Results"
          value={filteredKeywords.length}
          color="purple"
          loading={loading}
          error={!!error}
          icon={
            <svg className="w-6 h-6 text-purple-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
          }
        />
      </div>

      {/* Search and Actions */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div className="flex-1 max-w-md">
            <div className="relative">
              <input
                type="text"
                placeholder="Search keywords..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              />
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="w-5 h-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Add Keyword
            </button>
          </div>
        </div>

        {/* Active filters */}
        {searchTerm && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Active filters:</span>
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                Search: "{searchTerm}"
              </span>
              <button
                onClick={() => setSearchTerm('')}
                className="text-sm text-gray-600 hover:text-gray-800 underline ml-2"
              >
                Clear
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Keywords Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3">
          {[...Array(12)].map((_, index) => (
            <div key={index} className="bg-white p-3 rounded-lg border border-gray-200 animate-pulse">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="h-4 bg-gray-200 rounded w-20"></div>
                </div>
                <div className="flex gap-1">
                  <div className="w-6 h-6 bg-gray-200 rounded"></div>
                  <div className="w-6 h-6 bg-gray-200 rounded"></div>
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
            <h3 className="text-lg font-medium text-red-800 mb-2">Error Loading Keywords</h3>
            <p className="text-red-700 mb-4">{error}</p>
            <button
              onClick={fetchKeywords}
              className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      ) : filteredKeywords.length === 0 ? (
        <div className="text-center py-12">
          <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {searchTerm ? 'No Keywords Match Your Search' : 'No Keywords Found'}
          </h3>
          <p className="text-gray-500 mb-6">
            {searchTerm
              ? 'Try adjusting your search term or clear the filter to see all keywords.'
              : 'Start by adding your first keyword to organize your content.'
            }
          </p>
          {searchTerm ? (
            <button
              onClick={() => setSearchTerm('')}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Clear Search
            </button>
          ) : (
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Add Your First Keyword
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3">
          {filteredKeywords.map((keyword) => {
            const usageCount = keywordUsageCounts[keyword.keyword_id] || 0;
            return (
              <div key={keyword.keyword_id} className="bg-white p-3 rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-sm transition-all duration-200 group">
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      {editingKeyword?.keyword_id === keyword.keyword_id ? (
                        <input
                          type="text"
                          value={editingKeyword?.keyword_text || ''}
                          onChange={(e) => setEditingKeyword({
                            ...editingKeyword,
                            keyword_text: e.target.value
                          })}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                          autoFocus
                        />
                      ) : (
                        <span className="text-sm font-medium text-gray-800 truncate block">
                          {keyword.keyword_text}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1 ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      {editingKeyword?.keyword_id === keyword.keyword_id ? (
                        <>
                          <button
                            onClick={() => handleEditKeyword(keyword)}
                            className="text-green-600 hover:text-green-800 p-1 rounded hover:bg-green-50 transition-colors"
                            title="Save"
                          >
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                            </svg>
                          </button>
                          <button
                            onClick={() => setEditingKeyword(null)}
                            className="text-gray-600 hover:text-gray-800 p-1 rounded hover:bg-gray-50 transition-colors"
                            title="Cancel"
                          >
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => setEditingKeyword(keyword)}
                            className="text-blue-600 hover:text-blue-800 p-1 rounded hover:bg-blue-50 transition-colors"
                            title="Edit"
                          >
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleDeleteKeyword(keyword.keyword_id)}
                            className="text-red-600 hover:text-red-800 p-1 rounded hover:bg-red-50 transition-colors"
                            title="Delete"
                          >
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Usage stats and actions */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">
                        Used in {usageCount} {usageCount === 1 ? 'memory' : 'memories'}
                      </span>
                    </div>

                    {usageCount > 0 && (
                      <button
                        onClick={() => handleViewAssociations(keyword)}
                        className="text-xs text-blue-600 hover:text-blue-800 underline"
                        title="View associated memory blocks"
                      >
                        View memories
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Keyword Modal */}
      {showAddModal && (
        <Portal>
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Add New Keyword</h3>
            <div className="mb-4">
              <label htmlFor="keyword-text" className="block text-sm font-medium text-gray-700 mb-2">
                Keyword Text
              </label>
              <input
                type="text"
                id="keyword-text"
                value={newKeywordText}
                onChange={(e) => setNewKeywordText(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter keyword..."
                autoFocus
              />
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setNewKeywordText('');
                }}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddKeyword}
                disabled={!newKeywordText.trim()}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add Keyword
              </button>
            </div>
          </div>
        </div>
        </Portal>
      )}

      {/* Memory Block Associations Modal */}
      {showAssociationsModal && selectedKeyword && (
        <Portal>
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-blue-500 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4M4 7s-.5 1 .5 2M20 7s.5 1-.5 2m-19 5s.5-1-.5-2m19 5s-.5-1 .5-2" />
                  </svg>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800">
                      Memory Blocks with "{selectedKeyword.keyword_text}"
                    </h3>
                    <p className="text-sm text-gray-600">
                      {keywordUsageCounts[selectedKeyword.keyword_id] || 0} associated memories
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleCloseAssociationsModal}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
              {loadingAssociations ? (
                <div className="space-y-4">
                  {[...Array(3)].map((_, index) => (
                    <div key={index} className="bg-gray-50 p-4 rounded-lg animate-pulse">
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <div className="h-4 bg-gray-200 rounded w-32 mb-2"></div>
                          <div className="h-3 bg-gray-200 rounded w-full mb-1"></div>
                          <div className="h-3 bg-gray-200 rounded w-3/4"></div>
                        </div>
                        <div className="h-6 bg-gray-200 rounded w-16 ml-3"></div>
                      </div>
                      <div className="flex gap-2">
                        <div className="h-6 bg-gray-200 rounded-full w-16"></div>
                        <div className="h-6 bg-gray-200 rounded-full w-20"></div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : associatedMemoryBlocks.length === 0 ? (
                <div className="text-center py-8">
                  <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <p className="text-gray-500">No memory blocks found with this keyword</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {associatedMemoryBlocks.map((memoryBlock) => (
                    <div key={memoryBlock.id} className="bg-gray-50 p-4 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors">
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-sm font-medium text-gray-800">
                              Memory Block #{memoryBlock.id}
                            </span>
                            <span className="text-xs text-gray-500">
                              {memoryBlock.created_at ? new Date(memoryBlock.created_at).toLocaleDateString() : 'Unknown'}
                            </span>
                          </div>
                          <p className="text-sm text-gray-700 line-clamp-2">
                            {memoryBlock.content?.substring(0, 200)}
                            {memoryBlock.content && memoryBlock.content.length > 200 && '...'}
                          </p>
                        </div>
                        <div className="flex gap-2 ml-3">
                          <span className={`text-xs px-2 py-1 rounded-full ${
                            memoryBlock.archived
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-green-100 text-green-800'
                          }`}>
                            {memoryBlock.archived ? 'Archived' : 'Active'}
                          </span>
                        </div>
                      </div>

                      {memoryBlock.lessons_learned && (
                        <div className="mb-3">
                          <p className="text-xs text-gray-600">
                            <strong>Lessons:</strong> {memoryBlock.lessons_learned.substring(0, 150)}
                            {memoryBlock.lessons_learned.length > 150 && '...'}
                          </p>
                        </div>
                      )}

                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {memoryBlock.agent_id && (
                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                              Agent: {memoryBlock.agent_id}
                            </span>
                          )}
                          {memoryBlock.conversation_id && (
                            <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full">
                              Conv: {memoryBlock.conversation_id}
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => {
                            // This would open the memory block detail modal
                            // For now, just close this modal
                            handleCloseAssociationsModal();
                          }}
                          className="text-xs text-blue-600 hover:text-blue-800 underline"
                        >
                          View Details
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
        </Portal>
      )}
    </div>
  );
};

export default KeywordManager;
