import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import StatCard from './StatCard';
import MemoryBlockCard from './MemoryBlockCard';
import MemoryBlockPreviewModal from './MemoryBlockPreviewModal';
import memoryService from '../api/memoryService';
import agentService from '../api/agentService';
import { MemoryBlock } from '../api/memoryService';

interface StatInfo {
  count: number;
  loading: boolean;
  error: boolean;
}

interface DashboardStats {
  agents: StatInfo;
  memoryBlocks: StatInfo;
  conversations: StatInfo;
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats>({
    agents: { count: 0, loading: true, error: false },
    memoryBlocks: { count: 0, loading: true, error: false },
    conversations: { count: 0, loading: true, error: false }
  });
  const [recentMemoryBlocks, setRecentMemoryBlocks] = useState<MemoryBlock[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMemoryBlock, setSelectedMemoryBlock] = useState<MemoryBlock | null>(null);
  const [showMemoryModal, setShowMemoryModal] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch all stats in parallel
      const [agentsResponse, memoryBlocksResponse, conversationsResponse, recentBlocksResponse] = await Promise.allSettled([
        agentService.getAgents({ per_page: 1000 }),
        memoryService.getMemoryBlocks({ per_page: 1 }),
        fetchConversationsCount(),
        memoryService.getMemoryBlocks({
          per_page: 5,
          sort_by: 'created_at',
          sort_order: 'desc'
        })
      ]);

      // Update agents count
      if (agentsResponse.status === 'fulfilled') {
        const agentsCount = agentsResponse.value.items?.length || 0;
        setStats(prev => ({
          ...prev,
          agents: { count: agentsCount, loading: false, error: false }
        }));
      } else {
        setStats(prev => ({
          ...prev,
          agents: { count: 0, loading: false, error: true }
        }));
      }

      // Update memory blocks count
      if (memoryBlocksResponse.status === 'fulfilled') {
        const memoryBlocksCount = memoryBlocksResponse.value.total_items || 0;
        setStats(prev => ({
          ...prev,
          memoryBlocks: { count: memoryBlocksCount, loading: false, error: false }
        }));
      } else {
        setStats(prev => ({
          ...prev,
          memoryBlocks: { count: 0, loading: false, error: true }
        }));
      }

      // Update conversations count
      if (conversationsResponse.status === 'fulfilled') {
        const conversationsCount = conversationsResponse.value?.count || 0;
        setStats(prev => ({
          ...prev,
          conversations: { count: conversationsCount, loading: false, error: false }
        }));
      } else {
        setStats(prev => ({
          ...prev,
          conversations: { count: 0, loading: false, error: true }
        }));
      }

      // Update recent memory blocks
      if (recentBlocksResponse.status === 'fulfilled') {
        setRecentMemoryBlocks(recentBlocksResponse.value.items || []);
      } else {
        setRecentMemoryBlocks([]);
      }

    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError('Failed to load dashboard data');
      setStats(prev => ({
        agents: { ...prev.agents, loading: false, error: true },
        memoryBlocks: { ...prev.memoryBlocks, loading: false, error: true },
        conversations: { ...prev.conversations, loading: false, error: true }
      }));
    } finally {
      setLoading(false);
      // Update last updated timestamp
      setLastUpdated(new Date());
    }
  };

  const fetchConversationsCount = async () => {
    return memoryService.getConversationsCount();
  };

  const refreshData = () => {
    fetchDashboardData();
  };

  // Click handlers for navigation
  const handleStatCardClick = (statType: 'agents' | 'memoryBlocks' | 'conversations') => {
    switch(statType) {
      case 'agents':
        navigate('/agents');
        break;
      case 'memoryBlocks':
        navigate('/memory-blocks');
        break;
      case 'conversations':
        navigate('/analytics');
        break;
      default:
        break;
    }
  };

  // Click handler for memory blocks
  const handleMemoryBlockClick = (memoryBlock: MemoryBlock) => {
    setSelectedMemoryBlock(memoryBlock);
    setShowMemoryModal(true);
  };

  // Close modal handler
  const handleCloseModal = () => {
    setShowMemoryModal(false);
    setSelectedMemoryBlock(null);
  };

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          title="Total Agents"
          value={stats.agents.count}
          color="blue"
          loading={stats.agents.loading}
          error={stats.agents.error}
          onClick={() => handleStatCardClick('agents')}
          icon={
            <svg className="w-6 h-6 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M15 21a6 6 0 00-9-5.197M15 21a6 6 0 00-9-5.197" />
            </svg>
          }
        />

        <StatCard
          title="Memory Blocks"
          value={stats.memoryBlocks.count}
          color="purple"
          loading={stats.memoryBlocks.loading}
          error={stats.memoryBlocks.error}
          onClick={() => handleStatCardClick('memoryBlocks')}
          icon={
            <svg className="w-6 h-6 text-purple-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4M4 7s-.5 1 .5 2M20 7s.5 1-.5 2m-19 5s.5-1-.5-2m19 5s-.5-1 .5-2" />
            </svg>
          }
        />

        <StatCard
          title="Conversations"
          value={stats.conversations.count}
          color="green"
          loading={stats.conversations.loading}
          error={stats.conversations.error}
          onClick={() => handleStatCardClick('conversations')}
          icon={
            <svg className="w-6 h-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          }
        />
      </div>

      {/* Recent Memory Blocks Section */}
      <div className="bg-white p-6 rounded-lg shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-gray-500 mr-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
            </svg>
            <h3 className="text-lg font-semibold text-gray-800">Recent Memory Blocks</h3>
          </div>
          <div className="flex items-center gap-3">
            {lastUpdated && (
              <div className="text-sm text-gray-500 font-medium">
                Last updated: {lastUpdated.toLocaleString()}
              </div>
            )}
            <button
              onClick={refreshData}
              className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded transition duration-200 flex items-center"
              disabled={loading}
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>
        </div>

        {loading && recentMemoryBlocks.length === 0 ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, index) => (
              <div key={index} className="p-4 border border-gray-200 rounded-lg animate-pulse">
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 rounded w-32 mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-full mb-1"></div>
                    <div className="h-3 bg-gray-200 rounded w-3/4"></div>
                  </div>
                  <div className="h-6 bg-gray-200 rounded w-16 ml-3"></div>
                </div>
                <div className="flex gap-2 mb-3">
                  <div className="h-6 bg-gray-200 rounded-full w-16"></div>
                  <div className="h-6 bg-gray-200 rounded-full w-20"></div>
                </div>
                <div className="flex justify-between">
                  <div className="h-3 bg-gray-200 rounded w-20"></div>
                  <div className="h-3 bg-gray-200 rounded w-12"></div>
                </div>
              </div>
            ))}
          </div>
        ) : recentMemoryBlocks.length > 0 ? (
          <div className="space-y-4">
            {recentMemoryBlocks.map((memoryBlock) => (
              <MemoryBlockCard
                key={memoryBlock.id}
                memoryBlock={memoryBlock}
                onClick={() => handleMemoryBlockClick(memoryBlock)}
                onArchive={() => {}}
                onDelete={() => {}}
                onSuggestKeywords={() => {}}
                onCompactMemory={() => {}}
                availableAgents={[]}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            <p className="text-gray-500">No memory blocks found</p>
            <p className="text-sm text-gray-400 mt-1">Memory blocks will appear here once they're created</p>
          </div>
        )}

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-red-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        )}
      </div>

      {/* Memory Block Preview Modal */}
      {showMemoryModal && selectedMemoryBlock && (
        <MemoryBlockPreviewModal
          isOpen={showMemoryModal}
          onClose={handleCloseModal}
          memoryBlockId={selectedMemoryBlock.id}
        />
      )}
    </div>
  );
};

export default Dashboard;
