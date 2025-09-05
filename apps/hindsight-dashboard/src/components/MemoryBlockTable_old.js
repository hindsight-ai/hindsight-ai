import React, { useState, useMemo } from 'react';
import { CopyToClipboardButton } from './CopyToClipboardButton';
import { Link } from 'react-router-dom';
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels';

const MemoryBlockTable = React.forwardRef(({
  memoryBlocks,
  selectedMemoryBlocks,
  onSelectMemoryBlock,
  onSelectAllMemoryBlocks,
  sort,
  onSortChange,
  onActionChange,
  onKeywordClick,
  navigate,
  isArchivedView = false, // New prop to indicate if this is the archived view
  searchType = null, // New prop to indicate if advanced search is active
  showSearchScores = false, // New prop to show search scores
}, ref) => {
  const defaultHiddenColumns = isArchivedView 
    ? ['id', 'agent_id', 'conversation_id', 'keywords', 'errors'] 
    : ['id', 'agent_id', 'conversation_id', 'keywords', 'errors'];
  const [hiddenColumns] = useState(defaultHiddenColumns);

  const truncate = (text, length = 150) => {
    if (!text) return '';
    return text.length > length ? text.substring(0, length) + '...' : text;
  };

  const allColumnDefinitions = useMemo(() => [
    { id: 'select', label: '', size: 3 },
    { id: 'id', label: 'ID', size: 10, isSortable: true },
    { id: 'created_at', label: 'Creation Date', size: 7, isSortable: true },
    ...(isArchivedView ? [{ id: 'archived_at', label: 'Archived Date', size: 7, isSortable: true }] : []),
    ...(showSearchScores ? [{ id: 'search_score', label: 'Relevance', size: 8, isSortable: false }] : []),
    { id: 'lessons_learned', label: 'Lessons Learned', size: 75 },
    { id: 'keywords', label: 'Keywords', size: 15 },
    { id: 'errors', label: 'Errors', size: 15 },
    { id: 'agent_id', label: 'Agent ID', size: 10, isSortable: true },
    { id: 'conversation_id', label: 'Conversation ID', size: 10, isSortable: true },
    { id: 'feedback_score', label: 'Feedback', size: 10, isSortable: true },
    { id: 'actions', label: 'Actions', size: 5 },
  const columnDefinitions = useMemo(() => {
    return allColumnDefinitions.filter(col => !hiddenColumns.includes(col.id));
  }, [allColumnDefinitions, hiddenColumns]);

  const initialColumnLayout = useMemo(() => {
    return columnDefinitions.map(col => col.size);
  }, [columnDefinitions]);

  // Single layout state for all columns, managed by the header's PanelGroup
  const [columnLayout, setColumnLayout] = useState(initialColumnLayout);

  // Reset column layout when hiddenColumns change
  React.useEffect(() => {
    setColumnLayout(initialColumnLayout);
  }, [initialColumnLayout]);

  const renderHeader = () => (
    <div className="data-table-header" role="row">
      <PanelGroup direction="horizontal" onLayout={setColumnLayout} >
        {columnDefinitions.map((col, index) => (
          <React.Fragment key={col.id}>
            <Panel
              defaultSize={col.size}
              minSize={col.minSize !== undefined ? col.minSize : (col.id === 'select' ? 3 : (col.id === 'created_at' ? 7 : 5))}
              maxSize={col.maxSize !== undefined ? col.maxSize : undefined}
              style={{ padding: 0, margin: 0 }}
            >
              <div
                className={`header-cell ${col.isSortable ? 'sortable-header' : ''} ${col.id === 'select' ? 'checkbox-header' : ''}`}
                onClick={(e) => {
                  // Prevent click propagation for select column to avoid interfering with checkbox
                  if (col.id === 'select') {
                    e.stopPropagation();
                  } else if (col.isSortable) {
                    onSortChange(col.id);
                  }
                }}
                onKeyDown={(e) => {
                  if (col.id === 'select') {
                    // Allow keyboard navigation for checkbox
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      const checkbox = e.currentTarget.querySelector('input[type="checkbox"]');
                      if (checkbox) {
                        checkbox.click();
                      }
                    }
                  } else if (col.isSortable && (e.key === 'Enter' || e.key === ' ')) {
                    onSortChange(col.id);
                  }
                }}
                tabIndex={col.isSortable || col.id === 'select' ? 0 : -1}
                role="columnheader"
                aria-sort={sort.field === col.id ? (sort.order === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                {col.id === 'select' ? (
                  <input
                    type="checkbox"
                    onChange={onSelectAllMemoryBlocks}
                    checked={selectedMemoryBlocks.length === memoryBlocks.length && memoryBlocks.length > 0}
                    aria-label="Select all memory blocks"
                    style={{ pointerEvents: 'auto', cursor: 'pointer' }}
                  />
                ) : (
                  <>
                    {col.label}
                    {sort.field === col.id && <span className="sort-arrow">{sort.order === 'asc' ? '▲' : '▼'}</span>}
                  </>
                )}
              </div>
            </Panel>
            {index < columnDefinitions.length - 1 && <PanelResizeHandle className="resize-handle" />}
          </React.Fragment>
        ))}
      </PanelGroup>
    </div>
  );

  const renderRow = (block) => (
    <div className="data-table-row" key={block.id} role="row">
      {columnDefinitions.map((col, index) => (
        <React.Fragment key={col.id}>
          <div
            className="data-cell-wrapper"
            style={{ flexBasis: `${columnLayout[index]}%` }}
            role="cell"
          >
            <div className={`data-cell ${col.id}-cell`}>
              {renderCellContent(block, col.id)}
            </div>
          </div>
        </React.Fragment>
      ))}
    </div>
  );

  const renderCellContent = (block, columnId) => {
    switch (columnId) {
      case 'select':
        return (
          <input
            type="checkbox"
            checked={selectedMemoryBlocks.includes(block.id)}
            onChange={() => onSelectMemoryBlock(block.id)}
            style={{ pointerEvents: 'auto', cursor: 'pointer' }}
            onClick={(e) => e.stopPropagation()} // Prevent row click interference
          />
        );
      case 'id':
        return <CopyToClipboardButton textToCopy={block.id} displayId={truncate(block.id, 8)} />;
      case 'created_at':
        return new Date(block.created_at).toLocaleString();
      case 'archived_at':
        return block.archived_at ? new Date(block.archived_at).toLocaleString() : 'N/A';
      case 'lessons_learned':
        return (
          <>
            <span title={block.lessons_learned}>{truncate(block.lessons_learned)}</span>
            {block.lessons_learned && <CopyToClipboardButton textToCopy={block.lessons_learned} />}
          </>
        );
      case 'keywords':
        return block.keywords && block.keywords.length > 0 ? (
          <span className="keywords-list">
            {block.keywords.slice(0, 3).map((k) => (
              <span key={k.id} className="keyword-tag" onClick={() => onKeywordClick(k.keyword)} title={`Click to filter by ${k.keyword}`}>
                {k.keyword_text}
              </span>
            ))}
            {block.keywords.length > 3 && (
              <span className="more-keywords" title={block.keywords.map(k => k.keyword_text).join(', ')}>
                +{block.keywords.length - 3} more
              </span>
            )}
          </span>
        ) : '[]';
      case 'errors':
        return (
          <>
            <span title={block.errors}>{truncate(block.errors, 50)}</span>
            {block.errors && block.errors.length > 50 && (
              <Link to={`/memory-blocks/${block.id}`} className="read-more-link"> Read More</Link>
            )}
            {block.errors && <CopyToClipboardButton textToCopy={block.errors} />}
          </>
        );
      case 'agent_id':
        return <CopyToClipboardButton textToCopy={block.agent_id} displayId={truncate(block.agent_id, 8)} />;
      case 'conversation_id':
        return <CopyToClipboardButton textToCopy={block.conversation_id} displayId={truncate(block.conversation_id, 8)} />;
      case 'feedback_score':
        return (
          <div className="feedback-cell">
            <span className="feedback-score-display positive" title={`Positive Feedback: ${block.positive_feedback_count || 0}`}>
              👍 {block.positive_feedback_count || 0}
            </span>
            <span className="feedback-score-display negative" title={`Negative Feedback: ${block.negative_feedback_count || 0}`}>
              👎 {block.negative_feedback_count || 0}
            </span>
            <span className="retrieval-count-display" title={`Retrieval Count: ${block.retrieval_count}`}>
              📊 {block.retrieval_count}
            </span>
          </div>
        );
      case 'actions':
        return (
          <div className="actions-cell">
            <button
              onClick={() => navigate(`/memory-blocks/${block.id}`)}
              className="action-icon-button view-edit-button"
              title="View Details"
            >
              👁️
            </button>
            <button
              onClick={() => onActionChange({ target: { value: 'remove' } }, block.id)}
              className="action-icon-button remove-button"
              title="Delete Memory Block"
            >
              🗑️
            </button>
          </div>
 );
      default:
        return null;
    }
  };

  return (
    <div ref={ref} className="data-table-container" role="table" data-testid="data-table">
      {renderHeader()}
      <div className="data-table-body" role="rowgroup">
        {memoryBlocks.map(renderRow)}
      </div>
    </div>
  );
});

MemoryBlockTable.displayName = 'MemoryBlockTable';

export default MemoryBlockTable;
