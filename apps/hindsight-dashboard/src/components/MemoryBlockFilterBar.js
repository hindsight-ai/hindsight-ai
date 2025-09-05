import React from 'react';
import MultiSelectDropdown from './MultiSelectDropdown';
import RangeSlider from './RangeSlider';

const MemoryBlockFilterBar = ({
  filters,
  searchTerm, // New prop for immediate search input value
  agentIdInput, // New prop for local agent ID input value
  onFilterChange,
  onRangeFilterChange,
  onKeywordChange,
  onAgentIdApply, // New prop for applying agent ID filter
  availableKeywords,
  availableAgentIds = [], // Initialize with empty array to prevent undefined errors
  showFilters,
  toggleFilters,
  resetFilters,
  areFiltersActive,
  onApplyFilters, // This will be used if we add an explicit apply button
  // Advanced search props
  onSearchTypeChange,
  onAdvancedFilterChange,
  showAdvancedSearch = false,
  toggleAdvancedSearch
}) => {
  return (
    <div className="search-and-filters-section">
      <div className="search-bar-container">
        <label htmlFor="search-all-fields" className="visually-hidden">Search All Fields</label>
        <input
          type="text"
          id="search-all-fields"
          name="search"
          placeholder="Search by ID, Lessons Learned, Keywords, etc."
          value={searchTerm} // Use searchTerm for the input value
          onChange={onFilterChange}
          className="search-input-large"
        />
        <div className="filter-actions-group">
          {/* Advanced Search Toggle */}
          <button
            onClick={toggleAdvancedSearch}
            className={`advanced-search-toggle ${showAdvancedSearch ? 'active' : ''}`}
            title="Toggle advanced search options"
          >
            🔍 Advanced
          </button>
          {areFiltersActive() && (
            <button onClick={resetFilters} className="clear-filters-button">
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Advanced Search Controls */}
      {showAdvancedSearch && (
        <div className="advanced-search-container">
          <div className="advanced-search-grid">
            <div className="search-type-group">
              <label htmlFor="search-type">Search Type</label>
              <select
                id="search-type"
                name="search_type"
                value={filters.search_type || 'fulltext'}
                onChange={onFilterChange}
                className="search-type-select"
              >
                <option value="fulltext">Full-text (BM25)</option>
                <option value="semantic">Semantic</option>
                <option value="hybrid">Hybrid (BM25 + Semantic)</option>
              </select>
              <small className="help-text">
                Full-text finds exact matches, Semantic finds similar concepts, Hybrid combines both
              </small>
            </div>

            <div className="search-params-group">
              <label htmlFor="min-score">Minimum Score</label>
              <input
                type="number"
                id="min-score"
                name="min_score"
                value={filters.min_score || ''}
                onChange={onAdvancedFilterChange}
                min="0"
                max="1"
                step="0.1"
                placeholder="0.0"
                className="score-input"
              />
              <small className="help-text">Minimum relevance score (0.0-1.0)</small>
            </div>

            {filters.search_type === 'semantic' && (
              <div className="semantic-params-group">
                <label htmlFor="similarity-threshold">Similarity Threshold</label>
                <input
                  type="number"
                  id="similarity-threshold"
                  name="similarity_threshold"
                  value={filters.similarity_threshold || ''}
                  onChange={onAdvancedFilterChange}
                  min="0"
                  max="1"
                  step="0.05"
                  placeholder="0.7"
                  className="score-input"
                />
                <small className="help-text">Semantic similarity threshold (0.0-1.0)</small>
              </div>
            )}

            {filters.search_type === 'hybrid' && (
              <>
                <div className="weight-group">
                  <label htmlFor="fulltext-weight">Full-text Weight</label>
                  <input
                    type="number"
                    id="fulltext-weight"
                    name="fulltext_weight"
                    value={filters.fulltext_weight || ''}
                    onChange={onAdvancedFilterChange}
                    min="0"
                    max="1"
                    step="0.1"
                    placeholder="0.7"
                    className="score-input"
                  />
                  <small className="help-text">Weight for full-text score (0.0-1.0)</small>
                </div>
                <div className="weight-group">
                  <label htmlFor="semantic-weight">Semantic Weight</label>
                  <input
                    type="number"
                    id="semantic-weight"
                    name="semantic_weight"
                    value={filters.semantic_weight || ''}
                    onChange={onAdvancedFilterChange}
                    min="0"
                    max="1"
                    step="0.1"
                    placeholder="0.3"
                    className="score-input"
                  />
                  <small className="help-text">Weight for semantic score (0.0-1.0)</small>
                </div>
                <div className="combined-score-group">
                  <label htmlFor="min-combined-score">Min Combined Score</label>
                  <input
                    type="number"
                    id="min-combined-score"
                    name="min_combined_score"
                    value={filters.min_combined_score || ''}
                    onChange={onAdvancedFilterChange}
                    min="0"
                    max="1"
                    step="0.1"
                    placeholder="0.5"
                    className="score-input"
                  />
                  <small className="help-text">Minimum combined score (0.0-1.0)</small>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Always show filters for better UX - no toggle needed */}
      <div id="filters-container" className="filters-container">
        <div className="filter-group-grid">
          <div className={`filter-group id-filters ${filters.agent_id || filters.conversation_id ? 'active-filter' : ''}`}>
            <label htmlFor="agent-id">Agent ID</label>
            <input
              type="text"
              id="agent-id"
              name="agent_id"
              placeholder="Agent ID"
              value={agentIdInput} // Use agentIdInput for the input value
              onChange={onFilterChange}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  onAgentIdApply(e.target.value);
                }
              }}
              list="agent-ids" // Associate with datalist
            />
            <datalist id="agent-ids">
              {availableAgentIds.map((id) => (
                <option key={id} value={id} />
              ))}
            </datalist>
            <label htmlFor="conversation-id">Conversation ID</label>
            <input
              type="text"
              id="conversation-id"
              name="conversation_id"
              placeholder="Conversation ID"
              value={filters.conversation_id}
              onChange={onFilterChange}
            />
          </div>

          <div className={`filter-group score-count-filters ${filters.feedback_score_range[0] !== 0 || filters.feedback_score_range[1] !== 100 || filters.retrieval_count_range[0] !== 0 || filters.retrieval_count_range[1] !== 1000 ? 'active-filter' : ''}`}>
            <RangeSlider
              min={0}
              max={100}
              value={filters.feedback_score_range}
              onChange={(value) => onRangeFilterChange('feedback_score_range', value)}
              label="Feedback Score Range"
            />
            <RangeSlider
              min={0}
              max={1000}
              value={filters.retrieval_count_range}
              onChange={(value) => onRangeFilterChange('retrieval_count_range', value)}
              label="Retrieval Count Range"
            />
          </div>

          <div className={`filter-group date-filters ${filters.start_date || filters.end_date ? 'active-filter' : ''}`}>
            <label>Creation Date Range</label>
            <input
              type="date"
              name="start_date"
              value={filters.start_date}
              onChange={onFilterChange}
            />
            <input
              type="date"
              name="end_date"
              value={filters.end_date}
              onChange={onFilterChange}
            />
          </div>

          <div className={`filter-group keyword-filter ${filters.keywords.length > 0 ? 'active-filter' : ''}`}>
            <label htmlFor="keywords-select">Keywords</label>
            {availableKeywords && availableKeywords.length > 0 ? (
              <MultiSelectDropdown
                options={availableKeywords.map(keyword => ({ value: keyword.keyword_id, label: keyword.keyword_text }))}
                selectedValues={filters.keywords}
                onChange={onKeywordChange}
                placeholder="Select Keywords"
                data-testid="keyword-select"
              />
            ) : (
              <div data-testid="keyword-select" className="multi-select-dropdown-placeholder">
                No keywords available
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MemoryBlockFilterBar;
