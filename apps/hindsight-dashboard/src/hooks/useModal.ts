import { useState, useEffect } from 'react';

export interface UseModalResult {
  isOpen: boolean;
  openModal: () => void;
  closeModal: () => void;
  toggleModal: () => void;
  handleBackdropClick: (e: React.MouseEvent<HTMLDivElement>) => void;
  backdropClasses: string;
}

/**
 * Custom hook for modal functionality with ESC key and backdrop click support.
 */
const useModal = (initialState: boolean = false): UseModalResult => {
  const [isOpen, setIsOpen] = useState<boolean>(initialState);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
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

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      closeModal();
    }
  };

  const backdropClasses = 'fixed inset-0 bg-gray-900 bg-opacity-75 backdrop-blur-sm flex items-center justify-center z-50 p-4';

  return { isOpen, openModal, closeModal, toggleModal, handleBackdropClick, backdropClasses };
};

export default useModal;
