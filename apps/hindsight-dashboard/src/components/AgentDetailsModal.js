import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import agentService from '../api/agentService';
import memoryService from '../api/memoryService';

const AgentDetailsModal = ({ isOpen, onClose, agent, onAgentUpdated, onAgentDeleted }) => {
  const [activeTab, setActiveTab] = useState('details');
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    agent_name: '',
    description: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({
    memoryBlocks: 0,
    conversations: 0,
    loading: true
  });

  useEffect(() => {
    if (isOpen && agent) {
      setEditForm({
        agent_name: agent.agent_name || '',
        description: agent.description || ''
      });
      fetchAgentStats();
    }
  }, [isOpen, agent]);



  const fetchAgentStats = async () => {
    if (!agent) return;

    setStats(prev => ({ ...prev, loading: true }));
    try {
      // Fetch memory blocks count for this agent
      const memoryBlocksResponse = await memoryService.getMemoryBlocks({
        agent_id: agent.agent_id,
        per_page: 1
      });

      // For conversations, we'd need a specific endpoint
      // For now, we'll show memory blocks as a proxy
      setStats({
        memoryBlocks: memoryBlocksResponse.total_items || 0,
        conversations: 0, // Would need separate API call
        loading: false
      });
    } catch (err) {
      console.error('Failed to fetch agent stats:', err);
      setStats(prev => ({ ...prev, loading: false }));
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
    setError(null);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditForm({
      agent_name: agent?.agent_name || '',
      description: agent?.description || ''
    });
    setError(null);
  };

  const handleSaveEdit = async () => {
    if (!agent) return;

    if (!editForm.agent_name.trim()) {
      setError('Agent name cannot be empty');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await agentService.updateAgent(agent.agent_id, {
        agent_name: editForm.agent_name.trim(),
        description: editForm.description.trim()
      });

      setIsEditing(false);
      if (onAgentUpdated) {
        onAgentUpdated();
      }
    } catch (err) {
      console.error('Failed to update agent:', err);
      setError('Failed to update agent. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!agent) return;

    if (window.confirm('Are you sure you want to delete this agent and all its associated data (memory blocks, transcripts)? This action cannot be undone.')) {
      setLoading(true);
      try {
        await agentService.deleteAgent(agent.agent_id);
        onClose();
        if (onAgentDeleted) {
          onAgentDeleted();
        }
      } catch (err) {
        console.error('Failed to delete agent:', err);
        setError('Failed to delete agent. Please try again.');
      } finally {
        setLoading(false);
      }
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      // Could add a toast notification here
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  if (!isOpen || !agent) return null;

  // Handle click outside to close
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center z-[9999] p-4"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        minHeight: '100vh',
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        zIndex: 9999
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[85vh] overflow-hidden animate-in fade-in-0 zoom-in-95 duration-200 flex flex-col">
        {/* Header - Fixed at top */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center gap-4">
            <div className="bg-blue-100 p-3 rounded-lg">
              <svg className="w-6 h-6 text-blue-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 8V4H8"/>
                <rect x="4" y="8" width="8" height="12" rx="2"/>
                <path d="M8 12h4"/>
                <path d="M12 18h4"/>
                <path d="M16 12h4"/>
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">
                {isEditing ? 'Edit Agent' : agent.agent_name || 'Unnamed Agent'}
              </h2>
              <p className="text-sm text-gray-500">Agent Details & Management</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content - Scrollable */}
        <div className="p-6 overflow-y-auto flex-1 min-h-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading agent details...</p>
              </div>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md mx-auto">
                <svg className="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <h3 className="text-lg font-medium text-red-800 mb-2">Error Loading Details</h3>
                <p className="text-red-700 mb-4">{error}</p>
                <button
                  onClick={fetchAgentStats}
                  className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
                >
                  Try Again
                </button>
              </div>
            </div>
          ) : agent ? (
            <div className="space-y-6">
              {/* Basic Information */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-lg font-semibold text-gray-800 mb-3">Basic Information</h3>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Agent ID</label>
                      <div className="flex items-center gap-2">
                        <p className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded flex-1">{agent.agent_id}</p>
                        <button
                          onClick={() => copyToClipboard(agent.agent_id)}
                          className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors flex items-center gap-1"
                          title="Copy Agent ID"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                          <span className="text-sm">Copy</span>
                        </button>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Agent Name</label>
                      {isEditing ? (
                        <input
                          type="text"
                          value={editForm.agent_name}
                          onChange={(e) => setEditForm(prev => ({ ...prev, agent_name: e.target.value }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          placeholder="Enter agent name"
                        />
                      ) : (
                        <p className="text-gray-900 py-2">{agent.agent_name || 'Unnamed Agent'}</p>
                      )}
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-gray-800 mb-3">Timestamps</h3>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Created</label>
                      <p className="text-sm text-gray-600">{formatDateTime(agent.created_at)}</p>
                    </div>
                    {agent.updated_at && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700">Last Updated</label>
                        <p className="text-sm text-gray-600">{formatDateTime(agent.updated_at)}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Description */}
              {agent.description && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-800 mb-3">Description</h3>
                  {isEditing ? (
                    <textarea
                      value={editForm.description}
                      onChange={(e) => setEditForm(prev => ({ ...prev, description: e.target.value }))}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter agent description"
                    />
                  ) : (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">{agent.description}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Statistics */}
              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-3">Statistics</h3>
                {stats.loading ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-blue-50 p-4 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="bg-blue-100 p-2 rounded-lg">
                          <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4M4 7s-.5 1 .5 2M20 7s.5 1-.5 2m-19 5s.5-1-.5-2m19 5s-.5-1 .5-2" />
                          </svg>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-700">Memory Blocks</p>
                          <p className="text-2xl font-bold text-blue-600">{stats.memoryBlocks}</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-green-50 p-4 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="bg-green-100 p-2 rounded-lg">
                          <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                          </svg>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-700">Conversations</p>
                          <p className="text-2xl font-bold text-green-600">{stats.conversations}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
          {isEditing ? (
            <>
              <button
                onClick={handleCancelEdit}
                disabled={loading}
                className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                disabled={loading || !editForm.agent_name.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {loading && (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                )}
                Save Changes
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleDelete}
                disabled={loading}
                className="px-4 py-2 text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete Agent
              </button>
              <button
                onClick={handleEdit}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Edit Agent
              </button>
            </>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};

export default AgentDetailsModal;
