import React, { useState } from 'react';
import MemoryCompactionModal from './MemoryCompactionModal';
import { Agent } from '../api/agentService';
import { UIMemoryBlock } from '../types/domain';
import type { MemoryBlock as ApiMemoryBlock } from '../api/memoryService';
import notificationService from '../services/notificationService';

// Unified type combining API-required fields with optional UI extensions
interface ExtendedMemoryBlock extends UIMemoryBlock { agent_id?: string; agent_name?: string; priority?: string; category?: string; updated_at?: string; }

interface MemoryBlockCardProps {
  memoryBlock: ExtendedMemoryBlock; // may not have strict API required fields when coming from search etc.
  onClick?: (id: string) => void;
  onArchive: (id: string) => void;
  onDelete: (id: string) => void;
  onSuggestKeywords?: (id: string) => void;
  onCompactMemory?: (id: string, result: any) => void;
  availableAgents?: Agent[];
  llmEnabled?: boolean;
}

const MemoryBlockCard: React.FC<MemoryBlockCardProps> = ({ memoryBlock, onClick, onArchive, onDelete, onSuggestKeywords, onCompactMemory, availableAgents = [], llmEnabled = true }) => {
  const [showCompactionModal, setShowCompactionModal] = useState(false);
  const handleCompactClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!llmEnabled) {
      notificationService.showInfo('LLM features are currently disabled.');
      return;
    }
    setShowCompactionModal(true);
  };
  const handleCompactionApplied = (memoryId: string, compactionResult: any) => { onCompactMemory?.(memoryId, compactionResult); setShowCompactionModal(false); };
  const formatDate = (dateString?: string) => { if (!dateString) return 'Unknown'; const date = new Date(dateString); if (isNaN(date.getTime())) return 'Invalid Date'; return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }); };
  const getAgentName = () => { if (availableAgents?.length && memoryBlock.agent_id) { const agent = availableAgents.find(a => a.agent_id === memoryBlock.agent_id); if (agent?.agent_name) return agent.agent_name; } if ((memoryBlock as any).agent_name) return (memoryBlock as any).agent_name; if (memoryBlock.agent_id) return `Agent ${memoryBlock.agent_id.slice(-8)}`; return 'Unknown Agent'; };
  const getConversationName = () => memoryBlock.conversation_id ? `Conversation: ${memoryBlock.conversation_id.slice(-4)}` : 'No Conversation';
  const getKeywords = () => { const kw = (memoryBlock as any).keywords; if (Array.isArray(kw)) { return kw.map((k: any) => typeof k === 'string' ? k : (k.keyword_text || k.keyword || '')).filter(Boolean); } if (memoryBlock.content) { const words = memoryBlock.content.toLowerCase().split(/\s+/); const common = ['the','a','an','and','or','but','in','on','at','to','for','of','with','by']; return words.filter(w => w.length > 3 && !common.includes(w)).slice(0,5); } return []; };
  const getLessonsPreview = () => { if (memoryBlock.lessons_learned) return memoryBlock.lessons_learned.length > 150 ? `${memoryBlock.lessons_learned.substring(0,150)}...` : memoryBlock.lessons_learned; if (memoryBlock.content) return memoryBlock.content.length > 150 ? `${memoryBlock.content.substring(0,150)}...` : memoryBlock.content; return 'No content available'; };
  const getMetadata = () => { const metadata: Record<string, any> = {}; if (memoryBlock.feedback_score !== undefined) metadata.feedback_score = memoryBlock.feedback_score; if (memoryBlock.retrieval_count !== undefined) metadata.retrieval_count = memoryBlock.retrieval_count; if ((memoryBlock as any).priority) metadata.priority = (memoryBlock as any).priority; if ((memoryBlock as any).category) metadata.category = (memoryBlock as any).category; return metadata; };
  const keywords = getKeywords(); const metadata = getMetadata();
  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-all duration-200 cursor-pointer hover:border-blue-300" onClick={() => onClick?.(memoryBlock.id)}>
      {/* Header with Agent Info and Actions */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-start gap-4 flex-1">
          <div className="bg-purple-100 p-3 rounded-lg flex-shrink-0">
            <svg className="w-6 h-6 text-purple-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-semibold text-gray-800 truncate">{getConversationName()}</h4>
            <p className="text-sm text-gray-500">{getAgentName()} • {formatDate(memoryBlock.created_at || memoryBlock.timestamp)}</p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1 ml-4">
          {onSuggestKeywords && (
            <button
              onClick={(e) => {
                e.stopPropagation(); // Prevent card click when clicking button
                onSuggestKeywords(memoryBlock.id);
              }}
              className="p-2 hover:bg-blue-100 rounded-md transition-colors text-gray-400 hover:text-blue-500"
              title="Suggest Keywords"
            >
              <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
            </button>
          )}
          <button
            onClick={(e) => handleCompactClick(e)}
            className="p-2 hover:bg-green-100 rounded-md transition-colors text-gray-400 hover:text-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Compact Memory - Intelligently condense content"
            disabled={!llmEnabled}
          >
            <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation(); // Prevent card click when clicking archive
              onArchive(memoryBlock.id);
            }}
            className="p-2 hover:bg-red-100 rounded-md transition-colors text-gray-400 hover:text-red-500"
            title="Archive Memory Block"
          >
            <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      {/* Content Sections */}
      <div className="space-y-4">
        {/* Lessons Learned */}
        <div>
          <h5 className="text-sm font-medium text-gray-800 mb-2">Lessons Learned:</h5>
          <p className="text-sm text-gray-600 leading-relaxed">{getLessonsPreview()}</p>
        </div>

        {/* Keywords */}
        {keywords.length > 0 && (
          <div>
            <h5 className="text-sm font-medium text-gray-800 mb-2">Keywords:</h5>
            <div className="flex flex-wrap gap-2">
              {keywords.map((keyword, index) => (
                <span
                  key={index}
                  className="text-xs font-medium bg-gray-100 text-gray-700 px-2.5 py-1 rounded-full hover:bg-gray-200 transition-colors cursor-pointer"
                >
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Metadata */}
        {Object.keys(metadata).length > 0 && (
          <div>
            <h5 className="text-sm font-medium text-gray-800 mb-2">Metadata:</h5>
            <pre className="bg-gray-100 text-gray-800 text-xs p-3 rounded-lg overflow-x-auto font-mono">
              <code>{JSON.stringify(metadata, null, 2)}</code>
            </pre>
          </div>
        )}

        {/* Footer with timestamp and actions */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-100">
          <div className="text-xs text-gray-500">
            Created {formatDate(memoryBlock.created_at || memoryBlock.timestamp)}
            {memoryBlock.updated_at && memoryBlock.updated_at !== (memoryBlock.created_at || memoryBlock.timestamp) && (
              <span className="ml-2">
                • Updated {formatDate(memoryBlock.updated_at)}
              </span>
            )}
          </div>

          {/* Additional actions could go here */}
          <div className="flex items-center gap-1">
      {memoryBlock.feedback_score != null && (
              <span className={`text-xs px-2 py-1 rounded-full ${
        (memoryBlock.feedback_score ?? 0) >= 80 ? 'bg-green-100 text-green-800' :
        (memoryBlock.feedback_score ?? 0) >= 60 ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                {memoryBlock.feedback_score}/100
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Memory Compaction Modal */}
      <MemoryCompactionModal
        isOpen={showCompactionModal}
        onClose={() => setShowCompactionModal(false)}
        memoryBlock={memoryBlock as any as (ApiMemoryBlock & UIMemoryBlock)}
        onCompactionApplied={handleCompactionApplied}
        llmEnabled={llmEnabled}
      />
    </div>
  );
};

export default MemoryBlockCard;
