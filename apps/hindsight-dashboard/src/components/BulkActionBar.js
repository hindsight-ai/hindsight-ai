import React from 'react';

export const BulkActionBar = ({ selectedCount, onBulkRemove, onBulkTag, onBulkExport }) => {
  const isDisabled = selectedCount === 0;

  return (
    <div className="bulk-action-bar">
      <span className="selected-count">{selectedCount} items selected</span>
      <button onClick={onBulkRemove} disabled={isDisabled} className="bulk-remove-button">
        Remove ({selectedCount})
      </button>
      <button onClick={onBulkTag} disabled={isDisabled} className="bulk-tag-button">
        Tag ({selectedCount})
      </button>
      <button onClick={onBulkExport} disabled={isDisabled} className="bulk-export-button">
        Export ({selectedCount})
      </button>
    </div>
  );
};
