import React, { useState } from 'react';
import AddMemoryBlockModal from './AddMemoryBlockModal';
import './FloatingActionButton.css';

const FloatingActionButton = ({
  onMemoryBlockAdded,
  customIcon = "+",
  customTooltip = "Add Memory Block",
  customTestId = "fab-add-memory-block",
  children // For custom modal content
}) => {
  const [showModal, setShowModal] = useState(false);

  const handleClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('FAB clicked, opening modal'); // Debug log
    setShowModal(true);
  };

  const handleClose = () => {
    setShowModal(false);
  };

  const handleSuccess = () => {
    if (onMemoryBlockAdded) {
      onMemoryBlockAdded();
    }
  };

  return (
    <>
      <button
        className="fab"
        onClick={handleClick}
        aria-label={customTooltip}
        data-testid={customTestId}
      >
        <span className="fab-icon">{customIcon}</span>
        <span className="fab-tooltip">{customTooltip}</span>
      </button>

      {children ? (
        // If custom children (modal) provided, render them with modal state
        React.cloneElement(children, {
          isOpen: showModal,
          onClose: handleClose,
          onSuccess: handleSuccess
        })
      ) : (
        // Default to AddMemoryBlockModal
        <AddMemoryBlockModal
          isOpen={showModal}
          onClose={handleClose}
          onSuccess={handleSuccess}
        />
      )}
    </>
  );
};

export default FloatingActionButton;
