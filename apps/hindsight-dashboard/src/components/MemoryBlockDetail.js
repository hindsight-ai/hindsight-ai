import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import memoryService from '../api/memoryService';

const MemoryBlockDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [memoryBlock, setMemoryBlock] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({});
  const [availableKeywords, setAvailableKeywords] = useState([]);
  const [selectedKeywords, setSelectedKeywords] = useState([]);

  useEffect(() => {
    fetchMemoryBlockDetails();
    fetchKeywords();
  }, [id, fetchMemoryBlockDetails]);

  const fetchMemoryBlockDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await memoryService.getMemoryBlockById(id);
      setMemoryBlock(data);
      setFormData({
        errors: data.errors || '',
        lessons_learned: data.lessons_learned || '',
        external_history_link: data.external_history_link || '',
        feedback_score: data.feedback_score || 0,
        metadata: JSON.stringify(data.metadata, null, 2) || '{}',
      });
      setSelectedKeywords(data.keywords ? data.keywords.map(k => k.id) : []); // Ensure keywords is an array
    } catch (err) {
      setError('Failed to fetch memory block details: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchKeywords = async () => {
    try {
      const response = await memoryService.getKeywords();
      setAvailableKeywords(response);
    } catch (err) {
      console.error('Failed to fetch keywords:', err);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prevData) => ({
      ...prevData,
      [name]: value,
    }));
  };

  const handleKeywordSelectChange = (e) => {
    const { options } = e.target;
    const newSelectedKeywords = [];
    for (let i = 0, l = options.length; i < l; i++) {
      if (options[i].selected) {
        newSelectedKeywords.push(options[i].value);
      }
    }
    setSelectedKeywords(newSelectedKeywords);
  };

  const handleSave = async () => {
    setError(null);
    try {
      const updatedData = {
        ...formData,
        feedback_score: parseInt(formData.feedback_score, 10),
        metadata: JSON.parse(formData.metadata),
      };
      await memoryService.updateMemoryBlock(id, updatedData);

      // Update keyword associations
      const currentKeywordIds = memoryBlock.keywords.map(k => k.id);
      const keywordsToAdd = selectedKeywords.filter(kid => !currentKeywordIds.includes(kid));
      const keywordsToRemove = currentKeywordIds.filter(kid => !selectedKeywords.includes(kid));

      for (const keywordId of keywordsToAdd) {
        await memoryService.addKeywordToMemoryBlock(id, keywordId);
      }
      for (const keywordId of keywordsToRemove) {
        await memoryService.removeKeywordFromMemoryBlock(id, keywordId);
      }

      setIsEditing(false);
      fetchMemoryBlockDetails(); // Re-fetch to get the latest state including keyword names
    } catch (err) {
      setError('Failed to save changes: ' + err.message);
    }
  };

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this memory block?')) {
      setError(null);
      try {
        await memoryService.deleteMemoryBlock(id);
        navigate('/'); // Redirect to list after deletion
      } catch (err) {
        setError('Failed to delete memory block: ' + err.message);
      }
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
            <textarea name="metadata" value={formData.metadata} onChange={handleInputChange} rows="10" className="detail-value" />
          </div>
          <div className="detail-item">
            <label className="detail-label">Keywords:</label>
            <select multiple value={selectedKeywords} onChange={handleKeywordSelectChange} className="detail-value">
              {availableKeywords.map((keyword) => (
                <option key={keyword.id} value={keyword.id}>
                  {keyword.keyword}
                </option>
              ))}
            </select>
          </div>
          <button onClick={handleSave}>Save Changes</button>
          <button onClick={() => setIsEditing(false)}>Cancel</button>
        </>
      ) : (
        <>
          <div className="detail-item">
            <span className="detail-label">ID:</span>
            <span className="detail-value">{memoryBlock.id}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Agent ID:</span>
            <span className="detail-value">{memoryBlock.agent_id}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Conversation ID:</span>
            <span className="detail-value">{memoryBlock.conversation_id}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Creation Date:</span>
            <span className="detail-value">{new Date(memoryBlock.creation_date).toLocaleString()}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Feedback Score:</span>
            <span className="detail-value">{memoryBlock.feedback_score}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Retrieval Count:</span>
            <span className="detail-value">{memoryBlock.retrieval_count}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Errors:</span>
            <span className="detail-value">{memoryBlock.errors}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Lessons Learned:</span>
            <span className="detail-value">{memoryBlock.lessons_learned}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">External History Link:</span>
            <span className="detail-value">{memoryBlock.external_history_link}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Metadata:</span>
            <span className="detail-value"><pre>{JSON.stringify(memoryBlock.metadata, null, 2)}</pre></span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Keywords:</span>
            <span className="detail-value">{memoryBlock.keywords ? memoryBlock.keywords.map(k => k.keyword).join(', ') : 'N/A'}</span>
          </div>
          <button onClick={() => setIsEditing(true)}>Edit</button>
          <button onClick={handleDelete} className="delete-button">Delete</button>
        </>
      )}
      <button onClick={() => navigate('/')}>Back to List</button>
    </div>
  );
};

export default MemoryBlockDetail;
