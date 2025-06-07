import React from 'react';
import './MemoryBlockList.css'; // Assuming shared styles

const PaginationControls = ({
  pagination,
  onPageChange,
  onPerPageChange,
  onPageInputChange,
  fetchMemoryBlocks // Passed from parent for onBlur
}) => {
  return (
    <div className="pagination">
      <div className="pagination-per-page">
        <label htmlFor="per-page-select">Items per page:</label>
        <select
          id="per-page-select"
          name="per_page"
          value={pagination.per_page}
          onChange={onPerPageChange}
        >
          <option value="10">10</option>
          <option value="20">20</option>
          <option value="50">50</option>
          <option value="100">100</option>
        </select>
      </div>
      <div className="pagination-controls">
        <button
          onClick={() => onPageChange(1)}
          disabled={pagination.page === 1}
          title="First Page"
        >
          {'<<'}
        </button>
        <button
          onClick={() => onPageChange(pagination.page - 10)}
          disabled={pagination.page <= 10}
          title="Previous 10 Pages"
        >
          {'-10'}
        </button>
        <button
          onClick={() => onPageChange(pagination.page - 1)}
          disabled={pagination.page === 1}
          title="Previous Page"
        >
          Previous
        </button>
        <span className="pagination-page-info">
          Page{' '}
          <input
            type="number"
            value={pagination.page}
            onChange={onPageInputChange}
            onBlur={fetchMemoryBlocks}
            className="page-input"
            min="1"
            max={pagination.total_pages}
            aria-label={`Current page, out of ${pagination.total_pages}`}
          />{' '}
          of {pagination.total_pages}
        </span>
        <button
          onClick={() => onPageChange(pagination.page + 1)}
          disabled={pagination.page === pagination.total_pages}
          title="Next Page"
        >
          Next
        </button>
        <button
          onClick={() => onPageChange(pagination.page + 10)}
          disabled={pagination.page + 10 > pagination.total_pages}
          title="Next 10 Pages"
        >
          {'+10'}
        </button>
        <button
          onClick={() => onPageChange(pagination.total_pages)}
          disabled={pagination.page === pagination.total_pages}
          title="Last Page"
        >
          {'>>'}
        </button>
      </div>
      {pagination.total_items > 0 && (
        <span className="pagination-summary">
          Showing {(pagination.page - 1) * pagination.per_page + 1}-
          {Math.min(pagination.page * pagination.per_page, pagination.total_items)} of {pagination.total_items} results
        </span>
      )}
    </div>
  );
};

export default PaginationControls;
