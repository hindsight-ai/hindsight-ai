import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import memoryService from '../api/memoryService';
import notificationService from '../services/notificationService';
import { useAuth } from '../context/AuthContext';
import Button from './Button';

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
  const { features } = useAuth();
  const llmDisabled = !features.llmEnabled;
  const featureDisabled = !features.pruningEnabled;
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
    if (featureDisabled) {
      setSuggestions([]);
      setLoading(false);
      setError(null);
      return;
    }
    if (llmDisabled) {
      setLoading(false);
      setError(null);
      return;
    }
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
  }, [pruningParams, featureDisabled, llmDisabled]);

  useEffect(() => {
    if (featureDisabled) {
      setSuggestions([]);
      setSelectedBlocks([]);
    }
  }, [featureDisabled]);

  const handleParamChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setPruningParams(prev => ({
      ...prev,
      [name]: parseInt(value) || 0
    }));
  };

  const handleRefresh = () => {
    if (featureDisabled) {
      notificationService.showInfo('Feature coming soon.');
      return;
    }
    if (llmDisabled) {
      notificationService.showInfo('LLM features are currently disabled.');
      return;
    }
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

  if (featureDisabled) {
    return (
      <div className="p-6">
        <div className="max-w-3xl mx-auto text-center bg-gray-100 border border-dashed border-gray-300 rounded-xl p-10 text-gray-500">
          <h2 className="text-xl font-semibold text-gray-600 mb-2">Pruning</h2>
          <p className="text-sm text-gray-500">Feature coming soon.</p>
        </div>
      </div>
    );
  }

  // pruning_score semantics: lower = higher priority for pruning. So low
  // scores warn (red), high scores are safe to keep (green).
  const scoreBadgeClass = (score: number | string | undefined): string => {
    if (score === undefined || score === null || score === '') {
      return 'bg-red-100 text-red-700 border-red-200';
    }
    const numScore = typeof score === 'string' ? parseFloat(score) : score;
    if (numScore < 30) return 'bg-red-100 text-red-700 border-red-200';
    if (numScore < 70) return 'bg-amber-100 text-amber-700 border-amber-200';
    return 'bg-green-100 text-green-700 border-green-200';
  };

  const formatScore = (score: number | string | undefined): string => {
    if (score === undefined || score === null || score === '') return 'N/A';
    return (typeof score === 'string' ? parseFloat(score) : score).toFixed(2);
  };

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-6">
      {/* Pruning Parameters */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
        <h3 className="text-base font-semibold text-gray-900">Pruning Parameters</h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="space-y-1.5">
            <label htmlFor="batch_size" className="block text-sm font-medium text-gray-700">
              Batch Size
            </label>
            <input
              id="batch_size"
              type="number"
              name="batch_size"
              value={pruningParams.batch_size}
              onChange={handleParamChange}
              min={1}
              max={100}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
            />
            <small className="block text-xs text-gray-500">
              Number of memory blocks to evaluate in each batch (default: 50)
            </small>
          </div>
          <div className="space-y-1.5">
            <label htmlFor="target_count" className="block text-sm font-medium text-gray-700">
              Target Count
            </label>
            <input
              id="target_count"
              type="number"
              name="target_count"
              value={pruningParams.target_count || ''}
              onChange={handleParamChange}
              min={0}
              placeholder="Leave empty for no limit"
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
            />
            <small className="block text-xs text-gray-500">
              Maximum number of blocks to suggest for pruning (default: 100, leave empty for no limit)
            </small>
          </div>
          <div className="space-y-1.5">
            <label htmlFor="max_iterations" className="block text-sm font-medium text-gray-700">
              Max Iterations
            </label>
            <input
              id="max_iterations"
              type="number"
              name="max_iterations"
              value={pruningParams.max_iterations}
              onChange={handleParamChange}
              min={1}
              max={100}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
            />
            <small className="block text-xs text-gray-500">
              Maximum number of evaluation iterations to run (default: 10)
            </small>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button
            onClick={handleRefresh}
            disabled={loading || llmDisabled}
            title={llmDisabled ? 'LLM features are currently disabled' : undefined}
          >
            {loading ? 'Loading…' : 'Generate Suggestions'}
          </Button>
          {llmDisabled && (
            <p className="text-sm text-gray-500">LLM features are currently disabled. Generation is unavailable.</p>
          )}
        </div>
      </section>

      {/* Error */}
      {error && (
        <div
          className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          data-testid="error-message"
        >
          {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && suggestions.length === 0 && !error && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center text-sm text-gray-500">
          <p className="font-medium text-gray-700 mb-1">No pruning suggestions available</p>
          <p>Adjust the parameters and refresh to generate new suggestions.</p>
        </div>
      )}

      {/* Suggestions Table */}
      {suggestions.length > 0 && (
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 px-4 py-3">
            <div className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={selectedBlocks.length === suggestions.length && suggestions.length > 0}
                onChange={handleSelectAll}
                disabled={suggestions.length === 0}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                aria-label="Select all suggestions"
              />
              <span>{selectedBlocks.length} of {suggestions.length} selected</span>
            </div>
            <Button
              onClick={handleConfirmPruning}
              disabled={selectedBlocks.length === 0 || confirming}
            >
              {confirming ? 'Archiving…' : `Archive Selected (${selectedBlocks.length})`}
            </Button>
          </header>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                <tr>
                  <th scope="col" className="px-4 py-2 w-10">Select</th>
                  <th scope="col" className="px-4 py-2">ID</th>
                  <th scope="col" className="px-4 py-2">Score</th>
                  <th scope="col" className="px-4 py-2">Reason</th>
                  <th scope="col" className="px-4 py-2">Content</th>
                  <th scope="col" className="px-4 py-2">Created</th>
                  <th scope="col" className="px-4 py-2 w-16 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {suggestions.map((block) => (
                  <tr key={block.memory_block_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <input
                        type="checkbox"
                        checked={selectedBlocks.includes(block.memory_block_id)}
                        onChange={() => handleSelectBlock(block.memory_block_id)}
                        className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        aria-label={`Select suggestion ${block.memory_block_id.slice(0, 8)}`}
                      />
                    </td>
                    <td className="px-4 py-2 font-mono text-xs text-gray-600" title={block.memory_block_id}>
                      {truncate(block.memory_block_id, 8)}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${scoreBadgeClass(block.pruning_score)}`}
                      >
                        {formatScore(block.pruning_score)}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-700 max-w-xs truncate" title={block.rationale}>
                      {truncate(block.rationale || 'No reason provided', 50)}
                    </td>
                    <td className="px-4 py-2 text-gray-700 max-w-md truncate" title={block.content_preview}>
                      {truncate(block.content_preview || '', 100)}
                    </td>
                    <td className="px-4 py-2 text-gray-600 whitespace-nowrap">
                      {block.created_at ? new Date(block.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        type="button"
                        onClick={() => handleViewDetails(block.memory_block_id)}
                        className="inline-flex items-center justify-center rounded-md p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        title="View Details"
                        aria-label="View Details"
                      >
                        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12s3.75-7.5 9.75-7.5 9.75 7.5 9.75 7.5-3.75 7.5-9.75 7.5S2.25 12 2.25 12z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Loading State */}
      {loading && (
        <p className="text-sm text-gray-500" data-testid="loading-message">
          Generating pruning suggestions…
        </p>
      )}
    </div>
  );
};

export default PruningSuggestions;
