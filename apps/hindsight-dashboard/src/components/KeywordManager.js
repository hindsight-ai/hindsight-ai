import React, { useState, useEffect } from 'react';
import memoryService from '../api/memoryService';
import notificationService from '../services/notificationService';
import FloatingActionButton from './FloatingActionButton';
import AddKeywordModal from './AddKeywordModal';

const KeywordManager = () => {
  const [keywords, setKeywords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
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

  const handleKeywordAdded = () => {
    fetchKeywords(); // Refresh the list when a new keyword is added
  };

  const handleEditClick = (keyword) => {
    // For now, keep inline editing - could be moved to modal later
    setEditingKeywordId(keyword.id);
    setEditingKeywordText(keyword.keyword_text);
  };

  const handleSaveEdit = async (id) => {
    try {
      await memoryService.updateKeyword(id, { keyword_text: editingKeywordText });
      setEditingKeywordId(null);
      setEditingKeywordText('');
      fetchKeywords();
      notificationService.showSuccess('Keyword updated successfully');
    } catch (err) {
      notificationService.showError('Failed to update keyword: ' + err.message);
    }
  };

  const handleDeleteKeyword = async (id) => {
    if (window.confirm('Are you sure you want to delete this keyword?')) {
      try {
        await memoryService.deleteKeyword(id);
        fetchKeywords();
        notificationService.showSuccess('Keyword deleted successfully');
      } catch (err) {
        notificationService.showError('Failed to delete keyword: ' + err.message);
      }
    }
  };

  if (loading) return <p>Loading keywords...</p>;
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;

  return (
    <div className="keyword-manager-container">
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

      {/* Floating Action Button for adding keywords */}
      <FloatingActionButton
        onMemoryBlockAdded={handleKeywordAdded}
        customIcon="+"
        customTooltip="Add Keyword"
        customTestId="fab-add-keyword"
      >
        <AddKeywordModal />
      </FloatingActionButton>
    </div>
  );
};

export default KeywordManager;
