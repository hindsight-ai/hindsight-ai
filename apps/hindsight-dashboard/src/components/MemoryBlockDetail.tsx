import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import memoryService from '../api/memoryService';

interface KeywordItem { id: string; keyword: string; }
interface ExtendedMemoryBlock { id: string; agent_id?: string; conversation_id?: string; created_at?: string; timestamp?: string; feedback_score?: number | null; retrieval_count?: number | null; errors?: string; lessons_learned?: string; external_history_link?: string; metadata_col?: Record<string, any> | null; keywords?: { id: string; keyword: string }[]; }
interface FormState { errors: string; lessons_learned: string; external_history_link: string; feedback_score: number; metadata: string; }

const MemoryBlockDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [memoryBlock, setMemoryBlock] = useState<ExtendedMemoryBlock | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [formData, setFormData] = useState<FormState>({ errors: '', lessons_learned: '', external_history_link: '', feedback_score: 0, metadata: '{}' });
  const [availableKeywords, setAvailableKeywords] = useState<KeywordItem[]>([]);
  const [selectedKeywords, setSelectedKeywords] = useState<string[]>([]);

  const fetchMemoryBlockDetails = useCallback(async () => {
    if (!id) return;
    setLoading(true); setError(null);
    try {
      const data: any = await memoryService.getMemoryBlockById(id);
      setMemoryBlock(data);
      setFormData({ errors: data.errors || '', lessons_learned: data.lessons_learned || '', external_history_link: data.external_history_link || '', feedback_score: data.feedback_score || 0, metadata: data.metadata_col ? JSON.stringify(data.metadata_col, null, 2) : '{}' });
      setSelectedKeywords(data.keywords ? data.keywords.map((k: any) => k.id) : []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError('Failed to fetch memory block details: ' + msg);
    } finally { setLoading(false); }
  }, [id]);

  useEffect(() => { fetchMemoryBlockDetails(); fetchKeywords(); }, [id, fetchMemoryBlockDetails]);

  const fetchKeywords = async () => {
    try {
      const response: any[] = await memoryService.getKeywords();
      const normalized: KeywordItem[] = response.map(k => ({ id: (k.id ?? k.keyword_id) as string, keyword: (k.keyword ?? k.keyword_text) as string })).filter(k => !!k.id && !!k.keyword);
      setAvailableKeywords(normalized);
    } catch (err) { console.error('Failed to fetch keywords:', err); }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prevData => ({ ...prevData, [name]: name === 'feedback_score' ? Number(value) : value }));
  };

  const handleKeywordSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const { options } = e.target; const newSelected: string[] = [];
    for (let i = 0; i < options.length; i++) { if (options[i].selected) newSelected.push(options[i].value); }
    setSelectedKeywords(newSelected);
  };

  const handleSave = async () => {
    if (!id) return; setError(null);
    try {
      let parsedMeta: any; try { parsedMeta = JSON.parse(formData.metadata); } catch { throw new Error('Invalid JSON in metadata field'); }
      const updatedData: any = { errors: formData.errors, lessons_learned: formData.lessons_learned, external_history_link: formData.external_history_link, feedback_score: formData.feedback_score, metadata_col: parsedMeta };
      await memoryService.updateMemoryBlock(id, updatedData);
      const currentKeywordIds = (memoryBlock?.keywords || []).map(k => k.id);
      const toAdd = selectedKeywords.filter(kid => !currentKeywordIds.includes(kid));
      const toRemove = currentKeywordIds.filter(kid => !selectedKeywords.includes(kid));
      for (const keywordId of toAdd) { await memoryService.addKeywordToMemoryBlock(id, keywordId); }
      for (const keywordId of toRemove) { await memoryService.removeKeywordFromMemoryBlock(id, keywordId); }
      setIsEditing(false); fetchMemoryBlockDetails();
    } catch (err: unknown) { const msg = err instanceof Error ? err.message : 'Unknown error'; setError('Failed to save changes: ' + msg); }
  };

  const handleDelete = async () => {
    if (!id) return;
    if (window.confirm('Are you sure you want to delete this memory block?')) {
      setError(null);
      try { await memoryService.deleteMemoryBlock(id); navigate('/'); } catch (err: unknown) { const msg = err instanceof Error ? err.message : 'Unknown error'; setError('Failed to delete memory block: ' + msg); }
    }
  };

  if (loading) return <p>Loading memory block details...</p>;
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;
  if (!memoryBlock) return <p>Memory block not found.</p>;

  return (
    <div className="memory-block-detail-container">
      <h2>Memory Block Details</h2>
      {isEditing ? (
        <>
          <div className="detail-item">
            <label className="detail-label">Errors:</label>
            <textarea name="errors" value={formData.errors} onChange={handleInputChange} className="detail-value" />
          </div>
          <div className="detail-item">
            <label className="detail-label">Lessons Learned:</label>
            <textarea name="lessons_learned" value={formData.lessons_learned} onChange={handleInputChange} className="detail-value" />
          </div>
          <div className="detail-item">
            <label className="detail-label">External History Link:</label>
            <input type="text" name="external_history_link" value={formData.external_history_link} onChange={handleInputChange} className="detail-value" />
          </div>
            <div className="detail-item">
            <label className="detail-label">Feedback Score:</label>
            <input type="number" name="feedback_score" value={formData.feedback_score} onChange={handleInputChange} className="detail-value" />
          </div>
          <div className="detail-item">
            <label className="detail-label">Metadata (JSON):</label>
            <textarea name="metadata" value={formData.metadata} onChange={handleInputChange} rows={10} className="detail-value" />
          </div>
          <div className="detail-item">
            <label className="detail-label">Keywords:</label>
            <select multiple value={selectedKeywords} onChange={handleKeywordSelectChange} className="detail-value">
              {availableKeywords.map(keyword => (<option key={keyword.id} value={keyword.id}>{keyword.keyword}</option>))}
            </select>
          </div>
          <button onClick={handleSave}>Save Changes</button>
          <button onClick={() => setIsEditing(false)}>Cancel</button>
        </>
      ) : (
        <>
          <div className="detail-item"><span className="detail-label">ID:</span><span className="detail-value">{memoryBlock.id}</span></div>
          <div className="detail-item"><span className="detail-label">Agent ID:</span><span className="detail-value">{memoryBlock.agent_id}</span></div>
          <div className="detail-item"><span className="detail-label">Conversation ID:</span><span className="detail-value">{memoryBlock.conversation_id}</span></div>
          <div className="detail-item"><span className="detail-label">Creation Date:</span><span className="detail-value">{(() => { const date = memoryBlock.created_at || memoryBlock.timestamp; return date ? new Date(date).toLocaleString() : 'N/A'; })()}</span></div>
          <div className="detail-item"><span className="detail-label">Feedback Score:</span><span className="detail-value">{memoryBlock.feedback_score ?? 'N/A'}</span></div>
          <div className="detail-item"><span className="detail-label">Retrieval Count:</span><span className="detail-value">{memoryBlock.retrieval_count ?? 'N/A'}</span></div>
          <div className="detail-item"><span className="detail-label">Errors:</span><span className="detail-value">{memoryBlock.errors}</span></div>
          <div className="detail-item"><span className="detail-label">Lessons Learned:</span><span className="detail-value">{memoryBlock.lessons_learned}</span></div>
          <div className="detail-item"><span className="detail-label">External History Link:</span><span className="detail-value">{memoryBlock.external_history_link}</span></div>
          <div className="detail-item"><span className="detail-label">Metadata:</span><span className="detail-value"><pre>{memoryBlock.metadata_col && Object.keys(memoryBlock.metadata_col).length > 0 ? JSON.stringify(memoryBlock.metadata_col, null, 2) : 'N/A'}</pre></span></div>
          <div className="detail-item"><span className="detail-label">Keywords:</span><span className="detail-value">{memoryBlock.keywords ? memoryBlock.keywords.map(k => k.keyword).join(', ') : 'N/A'}</span></div>
          <button onClick={() => setIsEditing(true)}>Edit</button>
          <button onClick={handleDelete} className="delete-button">Delete</button>
        </>
      )}
      <button onClick={() => navigate('/')}>Back to List</button>
    </div>
  );
};

export default MemoryBlockDetail;
