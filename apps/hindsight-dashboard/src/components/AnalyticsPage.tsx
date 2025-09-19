import React, { useState, useEffect, useCallback } from 'react';
import agentService from '../api/agentService';
import memoryService from '../api/memoryService';
import { Agent } from '../api/agentService';
import { UIMemoryBlock } from '../types/domain';
import RefreshIndicator from './RefreshIndicator';
import usePageHeader from '../hooks/usePageHeader';

// Interfaces for analytics data
interface AgentWithStats extends Agent {
  conversationCount: number;
  memoryCount: number;
}

interface ConversationStats {
  id: string;
  agent_id: string;
  agent_name: string;
  memoryCount: number;
}

const AnalyticsPage: React.FC = () => {
  const [agents, setAgents] = useState<AgentWithStats[]>([]);
  const [conversations, setConversations] = useState<ConversationStats[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchAnalyticsData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch agents with their stats
      const agentsResponse = await agentService.getAgents({
        per_page: 100,
        sort_by: 'created_at',
        sort_order: 'desc'
      });

      // Fetch memory blocks to get conversation data
      const memoryBlocksResponse = await memoryService.getMemoryBlocks({
        per_page: 1000, // Get enough to analyze conversations
        sort_by: 'created_at',
        sort_order: 'desc'
      });

      const agentsArray: Agent[] = Array.isArray(agentsResponse) ? agentsResponse : (agentsResponse.items || []);
      const memoryBlocksArray: UIMemoryBlock[] = Array.isArray(memoryBlocksResponse) ? memoryBlocksResponse : (memoryBlocksResponse.items || []);

      // Process agents with conversation counts
      const agentsWithStats: AgentWithStats[] = agentsArray.map((agent: Agent) => {
        const agentMemories = memoryBlocksArray.filter((memory: UIMemoryBlock) => memory.agent_id === agent.agent_id);
        const uniqueConversations = new Set(agentMemories.map((memory: UIMemoryBlock) => memory.conversation_id)).size;

        return {
          ...agent,
          conversationCount: uniqueConversations,
          memoryCount: agentMemories.length
        };
      });

      // Process top conversations
      const conversationStats: Map<string, ConversationStats> = new Map();
      memoryBlocksArray.forEach((memory: UIMemoryBlock) => {
        const convId = memory.conversation_id;
        if (!convId) return;

        const agent = agentsArray.find((a: Agent) => a.agent_id === memory.agent_id);
        const agentName = agent?.agent_name || 'Unknown Agent';

        if (!conversationStats.has(convId)) {
          conversationStats.set(convId, {
            id: convId,
            agent_id: memory.agent_id || '',
            agent_name: agentName,
            memoryCount: 0
          });
        }
        const stats = conversationStats.get(convId)!;
        stats.memoryCount++;
      });

      const topConversations: ConversationStats[] = Array.from(conversationStats.values())
        .sort((a: ConversationStats, b: ConversationStats) => b.memoryCount - a.memoryCount)
        .slice(0, 10); // Top 10 conversations

      setAgents(agentsWithStats);
      setConversations(topConversations);

    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('Failed to fetch analytics data:', errorMessage);
      setError('Failed to load analytics data. Please try again.');
    } finally {
      setLoading(false);
      setLastUpdated(new Date());
    }
  }, []);

  useEffect(() => {
    void fetchAnalyticsData();
  }, [fetchAnalyticsData]);

  // Refresh when organization scope changes globally
  useEffect(() => {
    const handler = () => {
      fetchAnalyticsData();
    };
    window.addEventListener('orgScopeChanged', handler);
    return () => window.removeEventListener('orgScopeChanged', handler);
  }, [fetchAnalyticsData]);

  const handleRefresh = useCallback(() => {
    fetchAnalyticsData();
  }, [fetchAnalyticsData]);

  const { setHeaderContent, clearHeaderContent } = usePageHeader();

  useEffect(() => {
    setHeaderContent({
      description: 'Review performance trends across agents and conversations.',
      actions: (
        <RefreshIndicator lastUpdated={lastUpdated} onRefresh={handleRefresh} loading={loading} />
      )
    });

    return () => clearHeaderContent();
  }, [setHeaderContent, clearHeaderContent, lastUpdated, loading, handleRefresh]);

  const formatDate = (dateString: string | undefined): string => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md mx-auto">
          <svg className="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <h3 className="text-lg font-medium text-red-800 mb-2">Error Loading Analytics</h3>
          <p className="text-red-700 mb-4">{error}</p>
          <button
            onClick={fetchAnalyticsData}
            className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Agent Performance Section */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <div className="flex items-center mb-6">
          <svg className="w-5 h-5 text-gray-500 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M15 21a6 6 0 00-9-5.197M15 21a6 6 0 00-9-5.197" />
          </svg>
          <h3 className="text-lg font-semibold text-gray-800">Agent Performance</h3>
        </div>

        {agents.length === 0 ? (
          <div className="text-center py-8">
            <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M15 21a6 6 0 00-9-5.197M15 21a6 6 0 00-9-5.197" />
            </svg>
            <p className="text-gray-500">No agents found</p>
            <p className="text-sm text-gray-400 mt-1">Create agents to see performance analytics</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {agents.map((agent) => (
              <div key={agent.agent_id} className="flex justify-between items-center py-4">
                <div className="flex-1">
                  <p className="font-semibold text-gray-800">{agent.agent_name || 'Unnamed Agent'}</p>
                  <p className="text-xs text-gray-500 mt-1">{agent.conversationCount || 0} conversation{agent.conversationCount !== 1 ? 's' : ''} • {agent.memoryCount || 0} memories</p>
                </div>
                <div className="text-right ml-4">
                  <p className="text-xl font-bold text-gray-800">{agent.conversationCount || 0}</p>
                  <p className="text-xs text-gray-500">{agent.conversationCount || 0} conversation{agent.conversationCount !== 1 ? 's' : ''}</p>
                  <p className="text-xs text-gray-400 mt-1">{agent.memoryCount || 0} memories</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Top Conversations Section */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <div className="flex items-center mb-6">
          <svg className="w-5 h-5 text-gray-500 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <h3 className="text-lg font-semibold text-gray-800">Top Conversations</h3>
        </div>

        {conversations.length === 0 ? (
          <div className="text-center py-8">
            <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="text-gray-500">No conversations found</p>
            <p className="text-sm text-gray-400 mt-1">Conversations will appear here once they're created</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {conversations.map((conversation, index) => (
              <div key={conversation.id} className="flex justify-between items-center py-3">
                <div className="flex items-center gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium">
                    {index + 1}
                  </span>
                  <div>
                    <p className="font-semibold text-gray-800">{conversation.id}</p>
                    <p className="text-sm text-gray-600">Agent: {conversation.agent_name || 'Unknown Agent'}</p>
                  </div>
                </div>
                <span className="text-sm font-medium text-gray-700 bg-gray-100 px-3 py-1 rounded-md">
                  {conversation.memoryCount} memorie{conversation.memoryCount !== 1 ? 's' : 'y'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Additional Analytics Section - Memory Distribution */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <div className="flex items-center mb-6">
          <svg className="w-5 h-5 text-gray-500 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 className="text-lg font-semibold text-gray-800">Memory Distribution</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600 mb-2">
              {agents.reduce((total, agent) => total + (agent.memoryCount || 0), 0)}
            </div>
            <p className="text-sm text-gray-600">Total Memories</p>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600 mb-2">
              {agents.length}
            </div>
            <p className="text-sm text-gray-600">Active Agents</p>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600 mb-2">
              {conversations.length}
            </div>
            <p className="text-sm text-gray-600">Total Conversations</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;
