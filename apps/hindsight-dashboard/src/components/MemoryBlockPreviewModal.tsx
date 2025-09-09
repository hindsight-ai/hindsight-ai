import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import memoryService, { MemoryBlock } from '../api/memoryService';
import agentService, { Agent } from '../api/agentService';
import { UIMemoryBlock, UIMemoryKeyword } from '../types/domain';

interface MemoryBlockPreviewModalProps { isOpen: boolean; onClose: () => void; memoryBlockId: string | null; }

// Merge API block with UI optional fields
type PreviewMemoryBlock = (MemoryBlock & UIMemoryBlock) | null;

const MemoryBlockPreviewModal: React.FC<MemoryBlockPreviewModalProps> = ({ isOpen, onClose, memoryBlockId }) => {
  const [memoryBlock, setMemoryBlock] = useState<PreviewMemoryBlock>(null);
  const [agentInfo, setAgentInfo] = useState<Agent | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Handle click outside to close (without using useModal hook to avoid body scroll issues)
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  useEffect(() => {
    if (isOpen && memoryBlockId) {
      fetchMemoryBlockDetails();
    }
  }, [isOpen, memoryBlockId]);

  const fetchMemoryBlockDetails = async () => {
    if (!memoryBlockId) return;

    setLoading(true);
    setError(null);

    try {
  const response = await memoryService.getMemoryBlockById(memoryBlockId);
  setMemoryBlock(response as PreviewMemoryBlock);
      
      // Fetch agent information if agent_id is available
      if (response.agent_id) {
        try {
          const agentResponse = await agentService.getAgentById(response.agent_id);
          setAgentInfo(agentResponse);
        } catch (agentErr) {
          console.error('Failed to fetch agent details:', agentErr);
          // Continue without agent info, will fall back to agent_id display
        }
      }
    } catch (err) {
      console.error('Failed to fetch memory block details:', err);
      setError('Failed to load memory block details');
    } finally {
      setLoading(false);
    }
  };

  // Format date for display
  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Invalid Date';
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // Get agent name from agent_id or use a fallback
  const getAgentName = () => {
    if (!memoryBlock) return 'Unknown Agent';
    // First try to use fetched agent info
    if (agentInfo && agentInfo.agent_name) return agentInfo.agent_name;
    // Fallback to agent_name if it exists on the memory block itself
    if ((memoryBlock as any).agent_name) return (memoryBlock as any).agent_name as string;
    // Final fallback with shorter agent ID
    if (memoryBlock.agent_id) return `Agent ${memoryBlock.agent_id.slice(-8)}`;
    return 'Unknown Agent';
  };

  // Get conversation display name
  const getConversationName = () => {
    if (!memoryBlock) return 'No Conversation';
    if (memoryBlock.conversation_id) {
      return `Conversation: ${memoryBlock.conversation_id}`;
    }
    return 'No Conversation';
  };

  // Extract keywords from memory block
  const getKeywords = () => {
    if (!memoryBlock) return [];
    if (memoryBlock.keywords && Array.isArray(memoryBlock.keywords)) {
      // Handle both string keywords and keyword objects from backend
      return (memoryBlock.keywords as (string | UIMemoryKeyword)[]).map(keyword =>
        typeof keyword === 'string' ? keyword : (keyword.keyword_text || keyword.keyword || '')
      ).filter(Boolean);
    }
    if (memoryBlock.content) {
      // Simple keyword extraction from content
      const words = memoryBlock.content.toLowerCase().split(/\s+/);
      const commonWords = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'];
      return words
        .filter(word => word.length > 3 && !commonWords.includes(word))
        .slice(0, 8); // Show more keywords in modal
    }
    return [];
  };

  // Get metadata for display
  const getMetadata = () => {
    if (!memoryBlock) return {};
    const metadata: Record<string, any> = {};
    if (memoryBlock.feedback_score !== undefined) {
      metadata.feedback_score = memoryBlock.feedback_score;
    }
    if (memoryBlock.retrieval_count !== undefined) {
      metadata.retrieval_count = memoryBlock.retrieval_count;
    }
    // Optional UI-only fields if present
    if ((memoryBlock as any).priority) { metadata.priority = (memoryBlock as any).priority; }
    if ((memoryBlock as any).category) { metadata.category = (memoryBlock as any).category; }
    return metadata;
  };

  if (!isOpen) return null;

  const keywords = getKeywords();
  const metadata = getMetadata();

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
            <div className="bg-purple-100 p-3 rounded-lg">
              <svg className="w-6 h-6 text-purple-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">{getConversationName()}</h2>
              <p className="text-sm text-gray-500">{getAgentName()}</p>
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
                <p className="text-gray-600">Loading memory block details...</p>
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
                  onClick={fetchMemoryBlockDetails}
                  className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
                >
                  Try Again
                </button>
              </div>
            </div>
          ) : memoryBlock ? (
            <div className="space-y-6">
              {/* Basic Information */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-lg font-semibold text-gray-800 mb-3">Basic Information</h3>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Memory Block ID</label>
                      <p className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded">{memoryBlock.id}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Agent ID</label>
                      <p className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded">{memoryBlock.agent_id || 'N/A'}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Conversation ID</label>
                      <p className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded">{memoryBlock.conversation_id || 'N/A'}</p>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-gray-800 mb-3">Timestamps</h3>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Created</label>
                      <p className="text-sm text-gray-600">{formatDate(memoryBlock.created_at || memoryBlock.timestamp)}</p>
                    </div>
          {(memoryBlock as any).updated_at && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700">Last Updated</label>
            <p className="text-sm text-gray-600">{formatDate((memoryBlock as any).updated_at)}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Content */}
              {memoryBlock.content && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-800 mb-3">Content</h3>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">{memoryBlock.content}</p>
                  </div>
                </div>
              )}

              {/* Lessons Learned */}
              {memoryBlock.lessons_learned && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-800 mb-3">Lessons Learned</h3>
                  <div className="bg-blue-50 p-4 rounded-lg border-l-4 border-blue-400">
                    <p className="text-blue-800 whitespace-pre-wrap leading-relaxed">{memoryBlock.lessons_learned}</p>
                  </div>
                </div>
              )}

              {/* Keywords */}
              {keywords.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-800 mb-3">Keywords</h3>
                  <div className="flex flex-wrap gap-2">
                    {keywords.map((keyword, index) => (
                      <span
                        key={index}
                        className="text-sm font-medium bg-blue-100 text-blue-800 px-3 py-1 rounded-full"
                      >
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Quick Stats - Compact */}
              <div className="flex items-center gap-6 text-sm text-gray-600">
        {memoryBlock.feedback_score != null && (
                  <div className="flex items-center gap-2">
                    <span className="font-medium">Score:</span>
                    <span className={`font-semibold ${
          (memoryBlock.feedback_score ?? 0) >= 80 ? 'text-green-600' :
          (memoryBlock.feedback_score ?? 0) >= 60 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {memoryBlock.feedback_score}/100
                    </span>
                  </div>
                )}
                {memoryBlock.retrieval_count !== undefined && (
                  <div className="flex items-center gap-2">
                    <span className="font-medium">Views:</span>
                    <span className="font-semibold text-blue-600">{memoryBlock.retrieval_count}</span>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <span className="font-medium">Age:</span>
                  <span className="font-semibold text-purple-600">
                    {(() => {
                      const createdDate = memoryBlock.created_at || memoryBlock.timestamp;
                      if (!createdDate) return 'Unknown';
                      const date = new Date(createdDate);
                      if (isNaN(date.getTime())) return 'Invalid';
                      const nowMs = Date.now();
                      const createdMs = date.getTime();
                      if (isNaN(createdMs)) return 'Invalid';
                      const daysDiff = Math.floor((nowMs - createdMs) / (1000 * 60 * 60 * 24));
                      return `${daysDiff} days`;
                    })()}
                  </span>
                </div>
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default MemoryBlockPreviewModal;
