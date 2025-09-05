import { useState, useEffect } from 'react';

/**
 * Custom hook for modal functionality with click outside and ESC key support
 * @param {boolean} initialState - Initial modal state
 * @returns {Object} Modal state and handlers
 */
const useModal = (initialState = false) => {
  const [isOpen, setIsOpen] = useState(initialState);

  // Handle keyboard events (ESC to close)
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  const openModal = () => setIsOpen(true);
  const closeModal = () => setIsOpen(false);
  const toggleModal = () => setIsOpen(prev => !prev);

  // Handle click outside to close
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      closeModal();
    }
  };

  // Recommended backdrop classes for consistent styling
  const backdropClasses = "fixed inset-0 bg-gray-900 bg-opacity-75 backdrop-blur-sm flex items-center justify-center z-50 p-4";

  return {
    isOpen,
    openModal,
    closeModal,
    toggleModal,
    handleBackdropClick,
    backdropClasses,
  };
};

export default useModal;
