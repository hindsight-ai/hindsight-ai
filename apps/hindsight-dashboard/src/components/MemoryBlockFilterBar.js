import React from 'react';
import MultiSelectDropdown from './MultiSelectDropdown';
import RangeSlider from './RangeSlider';
import './MemoryBlockList.css'; // Assuming shared styles

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
  onApplyFilters // This will be used if we add an explicit apply button
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
          <button
            className="filter-toggle-button"
            onClick={toggleFilters}
            aria-expanded={showFilters}
            aria-controls="filters-container"
          >
            {showFilters ? 'Hide Filters ▲' : 'Apply Filters ▼'}
          </button>
          {areFiltersActive() && (
            <button onClick={resetFilters} className="clear-filters-button">
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {showFilters && (
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
              <MultiSelectDropdown
                options={availableKeywords.map(keyword => ({ value: keyword.keyword_id, label: keyword.keyword_text }))}
                selectedValues={filters.keywords}
                onChange={onKeywordChange}
                placeholder="Select Keywords"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MemoryBlockFilterBar;
