import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import memoryService from '../api/memoryService';

interface PruningSuggestion {
  memory_block_id: string;
  pruning_score?: number | string;
  rationale?: string;
  content_preview?: string;
  created_at?: string;
}

interface PruningParams {
  batch_size: number;
  target_count: number;
  max_iterations: number;
}

const PruningSuggestions: React.FC = () => {
  const [suggestions, setSuggestions] = useState<PruningSuggestion[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [confirming, setConfirming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedBlocks, setSelectedBlocks] = useState<string[]>([]);
  const [pruningParams, setPruningParams] = useState<PruningParams>({
    batch_size: 50,
    target_count: 100,
    max_iterations: 10
  });

  const navigate = useNavigate();

  const fetchPruningSuggestions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await memoryService.generatePruningSuggestions(pruningParams);
      const suggestionsData = response.suggestions || response.items || [];
      setSuggestions(suggestionsData);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError('Failed to fetch pruning suggestions: ' + errorMessage);
      console.error('Error fetching pruning suggestions:', err);
    } finally {
      setLoading(false);
    }
  }, [pruningParams]);

  const handleParamChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setPruningParams(prev => ({
      ...prev,
      [name]: parseInt(value) || 0
    }));
  };

  const handleRefresh = () => {
    fetchPruningSuggestions();
  };

  const handleSelectBlock = (id: string) => {
    setSelectedBlocks(prev => 
      prev.includes(id) 
        ? prev.filter(blockId => blockId !== id)
        : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (selectedBlocks.length === suggestions.length) {
      setSelectedBlocks([]);
    } else {
      setSelectedBlocks(suggestions.map(block => block.memory_block_id));
    }
  };

  const handleConfirmPruning = async () => {
    if (selectedBlocks.length === 0) {
      alert('Please select at least one memory block to prune.');
      return;
    }

    if (!window.confirm(`Are you sure you want to archive ${selectedBlocks.length} memory blocks for pruning? This action can be undone by unarchiving the blocks.`)) {
      return;
    }

    setConfirming(true);
    try {
      const response = await memoryService.confirmPruning(selectedBlocks);
      console.log('Pruning confirmed:', response);
      alert(`Successfully archived ${response.archived_count} memory blocks for pruning.`);
      
      // Refresh suggestions
      fetchPruningSuggestions();
      setSelectedBlocks([]);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError('Failed to confirm pruning: ' + errorMessage);
      console.error('Error confirming pruning:', err);
    } finally {
      setConfirming(false);
    }
  };

  const handleViewDetails = (id: string) => {
    navigate(`/memory-blocks/${id}`);
  };

  const truncate = (text: string, length = 100): string => {
    if (!text) return '';
    return text.length > length ? text.substring(0, length) + '...' : text;
  };

  return (
    <div className="memory-block-list-container">
      {/* Pruning Parameters */}
      <div className="pruning-params-section">
        <h3>Pruning Parameters</h3>
        <div className="pruning-params-form">
          <div className="form-group">
            <label>Batch Size:</label>
            <input
              type="number"
              name="batch_size"
              value={pruningParams.batch_size}
              onChange={handleParamChange}
              min="1"
              max="100"
            />
            <small className="param-hint">Number of memory blocks to evaluate in each batch (default: 50)</small>
          </div>
          <div className="form-group">
            <label>Target Count:</label>
            <input
              type="number"
              name="target_count"
              value={pruningParams.target_count || ''}
              onChange={handleParamChange}
              min="0"
              placeholder="Leave empty for no limit"
            />
            <small className="param-hint">Maximum number of blocks to suggest for pruning (default: 100, leave empty for no limit)</small>
          </div>
          <div className="form-group">
            <label>Max Iterations:</label>
            <input
              type="number"
              name="max_iterations"
              value={pruningParams.max_iterations}
              onChange={handleParamChange}
              min="1"
              max="100"
            />
            <small className="param-hint">Maximum number of evaluation iterations to run (default: 10)</small>
          </div>
          <button onClick={handleRefresh} disabled={loading}>
            {loading ? 'Loading...' : 'Generate Suggestions'}
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && <div className="error-message">{error}</div>}

      {/* Empty State */}
      {!loading && suggestions.length === 0 && !error && (
        <div className="empty-state-message">
          <p>No pruning suggestions available</p>
          <p>Adjust the parameters and refresh to generate new suggestions.</p>
        </div>
      )}

      {/* Suggestions Table */}
      {suggestions.length > 0 && (
        <div className="pruning-suggestions-container">
          <div className="bulk-action-bar">
            <div className="bulk-action-left">
              <input
                type="checkbox"
                checked={selectedBlocks.length === suggestions.length && suggestions.length > 0}
                onChange={handleSelectAll}
                disabled={suggestions.length === 0}
              />
              <span>{selectedBlocks.length} of {suggestions.length} selected</span>
            </div>
            <div className="bulk-action-right">
              <button 
                onClick={handleConfirmPruning} 
                disabled={selectedBlocks.length === 0 || confirming}
                className="confirm-pruning-button"
              >
                {confirming ? 'Archiving...' : `Archive Selected (${selectedBlocks.length})`}
              </button>
            </div>
          </div>

          <div className="data-table-container">
            <div className="data-table-header">
              <div className="header-cell">Select</div>
              <div className="header-cell">ID</div>
              <div className="header-cell">Score</div>
              <div className="header-cell">Reason</div>
              <div className="header-cell">Content</div>
              <div className="header-cell">Created</div>
              <div className="header-cell">Actions</div>
            </div>
            
            <div className="data-table-body">
              {suggestions.map((block) => (
                <div key={block.memory_block_id} className="data-table-row">
                  <div className="data-cell">
                    <input
                      type="checkbox"
                      checked={selectedBlocks.includes(block.memory_block_id)}
                      onChange={() => handleSelectBlock(block.memory_block_id)}
                    />
                  </div>
                  <div className="data-cell" title={block.memory_block_id}>
                    {truncate(block.memory_block_id, 8)}
                  </div>
                  <div className="data-cell">
                    <span className={`score-badge ${(() => {
                      const score = block.pruning_score;
                      if (score === undefined || score === null || score === '') return 'high';
                      const numScore = typeof score === 'string' ? parseFloat(score) : score;
                      return (numScore < 30) ? 'low' : (numScore < 70) ? 'medium' : 'high';
                    })()}`}>
                      {(() => {
                        const score = block.pruning_score;
                        return (score !== undefined && score !== null && score !== '') ? (typeof score === 'string' ? parseFloat(score) : score).toFixed(2) : 'N/A';
                      })()}
                    </span>
                  </div>
                  <div className="data-cell" title={block.rationale}>
                    {truncate(block.rationale || 'No reason provided', 50)}
                  </div>
                  <div className="data-cell" title={block.content_preview}>
                    {truncate(block.content_preview || '', 100)}
                  </div>
                  <div className="data-cell">
                    {block.created_at ? new Date(block.created_at).toLocaleDateString() : 'N/A'}
                  </div>
                  <div className="data-cell">
                    <button
                      onClick={() => handleViewDetails(block.memory_block_id)}
                      className="action-icon-button view-edit-button"
                      title="View Details"
                    >
                      👁️
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="loading-message">
          Generating pruning suggestions...
        </div>
      )}
    </div>
  );
};

export default PruningSuggestions;
