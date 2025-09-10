import React, { useState } from 'react';
import AddMemoryBlockModal from './AddMemoryBlockModal';

interface FloatingActionButtonProps {
  onMemoryBlockAdded?: () => void;
  customIcon?: string;
  customTooltip?: string;
  customTestId?: string;
  children?: React.ReactElement;
}

const FloatingActionButton: React.FC<FloatingActionButtonProps> = ({
  onMemoryBlockAdded,
  customIcon = "+",
  customTooltip = "Add Memory Block",
  customTestId = "fab-add-memory-block",
  children
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
        className="fixed bottom-6 right-6 w-14 h-14 bg-blue-500 hover:bg-blue-600 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center text-xl font-bold z-40"
        onClick={handleClick}
        aria-label={customTooltip}
        data-testid={customTestId}
      >
        {customIcon}
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
