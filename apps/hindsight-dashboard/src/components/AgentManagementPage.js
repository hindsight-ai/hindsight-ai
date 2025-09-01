import React, { useState, useEffect, useCallback } from 'react';
import agentService from '../api/agentService';
import AddAgentModal from './AddAgentModal';
import AgentDetailsModal from './AgentDetailsModal';

const AgentManagementPage = () => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await agentService.getAgents({
        per_page: 100, // Get all agents for card layout
        sort_by: 'created_at',
        sort_order: 'desc'
      });
      const agentsArray = Array.isArray(response) ? response : (response.items || []);
      setAgents(agentsArray);
    } catch (err) {
      console.error('Failed to fetch agents:', err);
      setError('Failed to load agents. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const handleAgentAdded = () => {
    fetchAgents(); // Refresh the list when a new agent is added
    setShowAddModal(false);
  };

  const handleDeleteAgent = async (agentId) => {
    if (window.confirm('Are you sure you want to delete this agent and all its associated data (memory blocks, transcripts)? This action cannot be undone.')) {
      try {
        await agentService.deleteAgent(agentId);
        await fetchAgents();
      } catch (err) {
        console.error('Failed to delete agent:', err);
        setError('Failed to delete agent. Please try again.');
      }
    }
  };

  const handleAgentClick = (agent) => {
    setSelectedAgent(agent);
    setShowDetailsModal(true);
  };

  const handleAgentUpdated = () => {
    fetchAgents();
  };

  const handleAgentDeleted = () => {
    fetchAgents();
  };

  const filteredAgents = agents.filter(agent =>
    agent.agent_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading agents...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 max-w-md mx-auto">
          <p className="text-red-700">{error}</p>
          <button
            onClick={fetchAgents}
            className="mt-4 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Create Agent Button */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Agents</h2>
          <p className="text-gray-500">Manage your AI agents</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="bg-gray-900 text-white px-4 py-2 rounded-lg flex items-center text-sm font-medium hover:bg-gray-800 transition-colors"
        >
          <svg className="w-4 h-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
          Create Agent
        </button>
      </div>

      {/* Search Bar */}
      <div className="max-w-md">
        <input
          type="text"
          placeholder="Search agents by name..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Agent Cards Grid */}
      {filteredAgents.length === 0 ? (
        <div className="text-center py-12">
          <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8V4H8"/><rect x="4" y="8" width="8" height="12" rx="2"/><path d="M8 12h4"/><path d="M12 18h4"/><path d="M16 12h4"/>
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No agents found</h3>
          <p className="text-gray-500 mb-6">
            {searchTerm ? 'No agents match your search.' : 'Get started by creating your first agent.'}
          </p>
          {!searchTerm && (
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Create Agent
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {filteredAgents.map((agent) => (
            <div
              key={agent.agent_id}
              className="bg-white p-5 rounded-xl shadow-sm border border-gray-200 flex justify-between items-start cursor-pointer hover:shadow-md hover:border-blue-300 transition-all duration-200"
              onClick={() => handleAgentClick(agent)}
            >
              <div className="flex items-start gap-4 flex-1">
                <div className="bg-blue-100 p-3 rounded-lg flex-shrink-0">
                  <svg className="w-6 h-6 text-blue-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 11H5a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2h-4m-4 0V9a2 2 0 1 1 4 0v2m-4 0a2 2 0 1 0 4 0m-5 8a2 2 0 1 0 0-4m5 0a2 2 0 1 0 0 4m0 0v2a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-2"/>
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-gray-800 truncate">{agent.agent_name || 'Unnamed Agent'}</h4>
                  <p className="text-sm text-gray-500">Created {formatDate(agent.created_at)}</p>
                  <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                    {agent.description || 'AI assistant for various tasks'}
                  </p>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation(); // Prevent card click when clicking delete
                  handleDeleteAgent(agent.agent_id);
                }}
                className="p-2 text-gray-400 hover:text-red-500 transition-colors flex-shrink-0"
                title="Delete Agent"
              >
                <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add Agent Modal */}
      {showAddModal && (
        <AddAgentModal
          onClose={() => setShowAddModal(false)}
          onAgentAdded={handleAgentAdded}
        />
      )}

      {/* Agent Details Modal */}
      {showDetailsModal && selectedAgent && (
        <AgentDetailsModal
          isOpen={showDetailsModal}
          onClose={() => {
            setShowDetailsModal(false);
            setSelectedAgent(null);
          }}
          agent={selectedAgent}
          onAgentUpdated={handleAgentUpdated}
          onAgentDeleted={handleAgentDeleted}
        />
      )}
    </div>
  );
};

export default AgentManagementPage;
