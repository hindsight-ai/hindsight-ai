import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import memoryService, { MemoryBlock } from '../api/memoryService';
import notificationService from '../services/notificationService';

// Keyword shape returned by getKeywords (not yet strongly typed in service)
interface KeywordItem { id: string; keyword: string; }

interface MemoryBlockDetailModalProps {
  blockId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

interface FormState {
  errors: string;
  lessons_learned: string;
  external_history_link: string;
  feedback_score: number;
  metadata: string; // JSON string
}

const MemoryBlockDetailModal: React.FC<MemoryBlockDetailModalProps> = ({ blockId, isOpen, onClose }) => {
  const [memoryBlock, setMemoryBlock] = useState<any | null>(null); // TODO: refine MemoryBlock extended type
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [formData, setFormData] = useState<FormState>({
    errors: '',
    lessons_learned: '',
    external_history_link: '',
    feedback_score: 0,
    metadata: '{}'
  });
  const [availableKeywords, setAvailableKeywords] = useState<KeywordItem[]>([]);
  const [selectedKeywords, setSelectedKeywords] = useState<string[]>([]);

  const fetchMemoryBlockDetails = useCallback(async () => {
    if (!blockId || !isOpen) return;
    setLoading(true);
    setError(null);
    try {
      const data: any = await memoryService.getMemoryBlockById(blockId);
      setMemoryBlock(data);
      setFormData({
        errors: data.errors || '',
        lessons_learned: data.lessons_learned || '',
        external_history_link: data.external_history_link || '',
        feedback_score: data.feedback_score || 0,
        metadata: data.metadata_col ? JSON.stringify(data.metadata_col, null, 2) : '{}',
      });
      setSelectedKeywords(data.keywords ? data.keywords.map((k: any) => k.id) : []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError('Failed to fetch memory block details: ' + msg);
      console.error('Error fetching memory block:', err);
    } finally {
      setLoading(false);
    }
  }, [blockId, isOpen]);

  const fetchKeywords = useCallback(async () => {
    if (!isOpen) return;
    try {
      const response: any[] = await memoryService.getKeywords();
      // Normalize expected fields (API appears to return either {id, keyword} or {keyword_id, keyword_text})
      const normalized: KeywordItem[] = response.map(k => ({
        id: (k.id ?? k.keyword_id) as string,
        keyword: (k.keyword ?? k.keyword_text) as string,
      })).filter(k => !!k.id && !!k.keyword);
      setAvailableKeywords(normalized);
    } catch (err) {
      console.error('Failed to fetch keywords:', err);
    }
  }, [isOpen]);

  useEffect(() => { if (isOpen && blockId) { fetchMemoryBlockDetails(); fetchKeywords(); } }, [blockId, isOpen, fetchMemoryBlockDetails, fetchKeywords]);

  useEffect(() => {
    const handleEscapeKey = (event: KeyboardEvent) => { if (event.key === 'Escape' && isOpen) { onClose(); } };
    if (isOpen) { document.addEventListener('keydown', handleEscapeKey); document.body.style.overflow = 'hidden'; }
    return () => { document.removeEventListener('keydown', handleEscapeKey); document.body.style.overflow = 'unset'; };
  }, [isOpen, onClose]);

  const handleSave = async () => {
    setError(null);
    try {
      let parsedMetadata: any;
      try { parsedMetadata = JSON.parse(formData.metadata); } catch { throw new Error('Invalid JSON in metadata field'); }
      await memoryService.updateMemoryBlock(blockId as string, {
        errors: formData.errors,
        lessons_learned: formData.lessons_learned,
        external_history_link: formData.external_history_link,
        feedback_score: formData.feedback_score,
        // API expects metadata_col
        metadata_col: parsedMetadata,
      } as any);
      const currentKeywordIds: string[] = (memoryBlock?.keywords || []).map((k: any) => k.id);
      const keywordsToAdd = selectedKeywords.filter(kid => !currentKeywordIds.includes(kid));
      const keywordsToRemove = currentKeywordIds.filter(kid => !selectedKeywords.includes(kid));
      for (const keywordId of keywordsToAdd) { await memoryService.addKeywordToMemoryBlock(blockId as string, keywordId); }
      for (const keywordId of keywordsToRemove) { await memoryService.removeKeywordFromMemoryBlock(blockId as string, keywordId); }
      setIsEditing(false);
      fetchMemoryBlockDetails();
      notificationService.showSuccess('Memory block updated successfully');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError('Failed to save changes: ' + msg);
      notificationService.showError('Failed to save changes: ' + msg);
    }
  };

  const handleDelete = async () => {
    if (!blockId) return;
    if (window.confirm('Are you sure you want to delete this memory block?')) {
      setError(null);
      try {
        await memoryService.deleteMemoryBlock(blockId);
        notificationService.showSuccess('Memory block deleted successfully');
        onClose();
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        setError('Failed to delete memory block: ' + msg);
        notificationService.showError('Failed to delete memory block: ' + msg);
      }
    }
  };

  const handleInputChange = (field: keyof FormState, value: string | number) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => { if (e.target === e.currentTarget) { onClose(); } };

  return createPortal(
    <div 
      className="fixed inset-0 bg-black/40 backdrop-blur-sm overflow-y-auto h-full w-full z-[9999] flex items-start justify-center p-4"
      onClick={handleBackdropClick}
    >
      <div className="relative mt-8 mx-auto p-5 border border-gray-200 w-11/12 max-w-4xl shadow-xl rounded-lg bg-white animate-in fade-in-0 zoom-in-95 duration-200"
           onClick={(e) => e.stopPropagation()}
      >
        <div className="mt-3">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-semibold text-gray-900">Memory Block Details</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="max-h-[70vh] overflow-y-auto"
               style={{ maxHeight: 'calc(90vh - 200px)' }}
          >
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-3 text-gray-600">Loading memory block details...</span>
              </div>
            ) : error ? (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                <p className="text-red-700">Error: {error}</p>
              </div>
            ) : !memoryBlock ? (
              <div className="text-center py-8">
                <p className="text-gray-500">Memory block not found.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {isEditing ? (
                  <>
                    {/* Edit Mode */}
                    <div className="grid grid-cols-1 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Errors</label>
                        <textarea
                          value={formData.errors}
                          onChange={(e) => handleInputChange('errors', e.target.value)}
                          className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                          rows={3}
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Lessons Learned</label>
                        <textarea
                          value={formData.lessons_learned}
                          onChange={(e) => handleInputChange('lessons_learned', e.target.value)}
                          className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                          rows={3}
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">External History Link</label>
                        <input
                          type="url"
                          value={formData.external_history_link}
                          onChange={(e) => handleInputChange('external_history_link', e.target.value)}
                          className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Feedback Score</label>
                        <input
                          type="number"
                          value={formData.feedback_score}
                          onChange={(e) => handleInputChange('feedback_score', parseInt(e.target.value) || 0)}
                          className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Metadata (JSON)</label>
                        <textarea
                          value={formData.metadata}
                          onChange={(e) => handleInputChange('metadata', e.target.value)}
                          className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 font-mono text-sm"
                          rows={6}
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Keywords</label>
                        <div className="space-y-2 max-h-32 overflow-y-auto border border-gray-200 rounded-md p-2">
                          {availableKeywords.map(keyword => (
                            <label key={keyword.id} className="flex items-center">
                              <input
                                type="checkbox"
                                checked={selectedKeywords.includes(keyword.id)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedKeywords(prev => [...prev, keyword.id]);
                                  } else {
                                    setSelectedKeywords(prev => prev.filter(id => id !== keyword.id));
                                  }
                                }}
                                className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                              />
                              <span className="ml-2 text-sm text-gray-700">{keyword.keyword}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    {/* View Mode */}
                    <div className="grid grid-cols-1 gap-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-sm font-medium text-gray-500">ID:</span>
                          <p className="text-sm text-gray-900 font-mono break-all">{memoryBlock.id}</p>
                        </div>
                        <div>
                          <span className="text-sm font-medium text-gray-500">Agent ID:</span>
                          <p className="text-sm text-gray-900">{memoryBlock.agent_id || 'N/A'}</p>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-sm font-medium text-gray-500">Conversation ID:</span>
                          <p className="text-sm text-gray-900 font-mono break-all">{memoryBlock.conversation_id || 'N/A'}</p>
                        </div>
                        <div>
                          <span className="text-sm font-medium text-gray-500">Creation Date:</span>
                          <p className="text-sm text-gray-900">
                            {(() => {
                              const date = memoryBlock.created_at || memoryBlock.timestamp;
                              return date ? new Date(date).toLocaleString() : 'N/A';
                            })()}
                          </p>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-sm font-medium text-gray-500">Feedback Score:</span>
                          <p className="text-sm text-gray-900">
                            {memoryBlock.feedback_score !== null && memoryBlock.feedback_score !== undefined ? memoryBlock.feedback_score : 'N/A'}
                          </p>
                        </div>
                        <div>
                          <span className="text-sm font-medium text-gray-500">Retrieval Count:</span>
                          <p className="text-sm text-gray-900">
                            {memoryBlock.retrieval_count !== null && memoryBlock.retrieval_count !== undefined ? memoryBlock.retrieval_count : 'N/A'}
                          </p>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-sm font-medium text-gray-500">Age:</span>
                          <p className="text-sm text-gray-900">
                            {(() => {
                              const createdDate = memoryBlock.created_at || memoryBlock.timestamp;
                              if (!createdDate) return 'Unknown';
                              const date = new Date(createdDate);
                              if (isNaN(date.getTime())) return 'Invalid';
                              const daysDiff = Math.floor((Date.now() - date.getTime()) / (1000 * 60 * 60 * 24));
                              if (daysDiff === 0) return 'Today';
                              if (daysDiff === 1) return '1 day';
                              return `${daysDiff} days`;
                            })()}
                          </p>
                        </div>
                        <div>
                          <span className="text-sm font-medium text-gray-500">Status:</span>
                          <p className="text-sm text-gray-900">
                            {memoryBlock.archived ? (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                Archived
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                Active
                              </span>
                            )}
                          </p>
                        </div>
                      </div>
                      
                      {memoryBlock.content && (
                        <div>
                          <span className="text-sm font-medium text-gray-500">Content:</span>
                          <div className="mt-1 p-3 bg-gray-50 rounded-md border">
                            <p className="text-sm text-gray-900 whitespace-pre-wrap">{memoryBlock.content}</p>
                          </div>
                        </div>
                      )}
                      
                      {memoryBlock.errors && (
                        <div>
                          <span className="text-sm font-medium text-gray-500">Errors:</span>
                          <div className="mt-1 p-3 bg-red-50 rounded-md border border-red-200">
                            <p className="text-sm text-red-900">{memoryBlock.errors}</p>
                          </div>
                        </div>
                      )}
                      
                      {memoryBlock.lessons_learned && (
                        <div>
                          <span className="text-sm font-medium text-gray-500">Lessons Learned:</span>
                          <div className="mt-1 p-3 bg-blue-50 rounded-md border border-blue-200">
                            <p className="text-sm text-blue-900">{memoryBlock.lessons_learned}</p>
                          </div>
                        </div>
                      )}
                      
                      {memoryBlock.external_history_link && (
                        <div>
                          <span className="text-sm font-medium text-gray-500">External History Link:</span>
                          <p className="text-sm text-blue-600 break-all">
                            <a href={memoryBlock.external_history_link} target="_blank" rel="noopener noreferrer" className="hover:underline">
                              {memoryBlock.external_history_link}
                            </a>
                          </p>
                        </div>
                      )}
                      
                      <div>
                        <span className="text-sm font-medium text-gray-500">Metadata:</span>
                        <div className="mt-1 p-3 bg-gray-50 rounded-md border">
                          <pre className="text-xs text-gray-900 whitespace-pre-wrap overflow-x-auto">
                            {memoryBlock.metadata_col && Object.keys(memoryBlock.metadata_col).length > 0 
                              ? JSON.stringify(memoryBlock.metadata_col, null, 2) 
                              : 'N/A'}
                          </pre>
                        </div>
                      </div>
                      
                      <div>
                        <span className="text-sm font-medium text-gray-500">Keywords:</span>
                        <div className="mt-1">
                          {memoryBlock.keywords && memoryBlock.keywords.length > 0 ? (
                            <div className="flex flex-wrap gap-2">
                              {memoryBlock.keywords.map((keyword: any) => (
                                <span key={keyword.id} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                  {keyword.keyword}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <p className="text-sm text-gray-500">No keywords assigned</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Actions */}
          {!loading && !error && memoryBlock && (
            <div className="flex items-center justify-between pt-4 border-t border-gray-200 mt-6">
              <div className="flex items-center gap-3">
                {isEditing ? (
                  <>
                    <button
                      onClick={handleSave}
                      className="px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700"
                    >
                      Save Changes
                    </button>
                    <button
                      onClick={() => setIsEditing(false)}
                      className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => setIsEditing(true)}
                      className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
                    >
                      Edit
                    </button>
                    <button
                      onClick={handleDelete}
                      className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700"
                    >
                      Delete
                    </button>
                  </>
                )}
              </div>
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};

export default MemoryBlockDetailModal;
