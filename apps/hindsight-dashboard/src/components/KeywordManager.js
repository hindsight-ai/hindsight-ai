import React, { useState, useEffect } from 'react';
import memoryService from '../api/memoryService';

const KeywordManager = () => {
  const [keywords, setKeywords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newKeyword, setNewKeyword] = useState('');
  const [editingKeywordId, setEditingKeywordId] = useState(null);
  const [editingKeywordText, setEditingKeywordText] = useState('');

  useEffect(() => {
    fetchKeywords();
  }, []);

  const fetchKeywords = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await memoryService.getKeywords();
      setKeywords(data);
    } catch (err) {
      setError('Failed to fetch keywords: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddKeyword = async () => {
    if (!newKeyword.trim()) return;
    setError(null);
    try {
      await memoryService.createKeyword({ keyword: newKeyword });
      setNewKeyword('');
      fetchKeywords();
    } catch (err) {
      setError('Failed to add keyword: ' + err.message);
    }
  };

  const handleEditClick = (keyword) => {
    setEditingKeywordId(keyword.id);
    setEditingKeywordText(keyword.keyword_text);
  };

  const handleSaveEdit = async (id) => {
    setError(null);
    try {
      await memoryService.updateKeyword(id, { keyword_text: editingKeywordText });
      setEditingKeywordId(null);
      setEditingKeywordText('');
      fetchKeywords();
    } catch (err) {
      setError('Failed to update keyword: ' + err.message);
    }
  };

  const handleDeleteKeyword = async (id) => {
    if (window.confirm('Are you sure you want to delete this keyword?')) {
      setError(null);
      try {
        await memoryService.deleteKeyword(id);
        fetchKeywords();
      } catch (err) {
        setError('Failed to delete keyword: ' + err.message);
      }
    }
  };

  if (loading) return <p>Loading keywords...</p>;
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;

  return (
    <div className="keyword-manager-container">
      <h2>Keyword Manager</h2>

      <div className="add-keyword">
        <input
          type="text"
          placeholder="New Keyword"
          value={newKeyword}
          onChange={(e) => setNewKeyword(e.target.value)}
        />
        <button onClick={handleAddKeyword}>Add Keyword</button>
      </div>

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Keyword</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {keywords.map((keyword) => (
            <tr key={keyword.id}>
              <td>{keyword.id}</td>
              <td>
                {editingKeywordId === keyword.id ? (
                  <input
                    type="text"
                    value={editingKeywordText}
                    onChange={(e) => setEditingKeywordText(e.target.value)}
                  />
                ) : (
                  keyword.keyword_text
                )}
              </td>
              <td>
                {editingKeywordId === keyword.id ? (
                  <>
                    <button onClick={() => handleSaveEdit(keyword.id)}>Save</button>
                    <button onClick={() => setEditingKeywordId(null)}>Cancel</button>
                  </>
                ) : (
                  <>
                    <button onClick={() => handleEditClick(keyword)}>Edit</button>
                    <button onClick={() => handleDeleteKeyword(keyword.id)} className="delete-button">Delete</button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default KeywordManager;
