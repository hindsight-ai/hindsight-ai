import React from 'react';
import './KeyboardShortcutHelp.css';

const KeyboardShortcutHelp = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const shortcuts = [
    { keys: ['Ctrl', '/'], description: 'Show/hide keyboard shortcuts' },
    { keys: ['Ctrl', 'B'], description: 'Toggle sidebar collapse' },
    { keys: ['Tab'], description: 'Navigate between focusable elements' },
    { keys: ['Enter'], description: 'Activate focused element' },
    { keys: ['Escape'], description: 'Close modals and menus' },
    { keys: ['↑', '↓'], description: 'Navigate lists and menus' },
    { keys: ['Space'], description: 'Select/deselect items' },
  ];

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div
      className="keyboard-shortcuts-overlay"
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      data-testid="keyboard-shortcuts-overlay"
    >
      <div className="keyboard-shortcuts-modal">
        <div className="keyboard-shortcuts-header">
          <h2>Keyboard Shortcuts</h2>
          <button
            className="close-button"
            onClick={onClose}
            aria-label="Close keyboard shortcuts"
            data-testid="close-shortcuts"
          >
            ×
          </button>
        </div>

        <div className="keyboard-shortcuts-content">
          <div className="shortcuts-list">
            {shortcuts.map((shortcut, index) => (
              <div key={index} className="shortcut-item">
                <div className="shortcut-keys">
                  {shortcut.keys.map((key, keyIndex) => (
                    <React.Fragment key={keyIndex}>
                      <kbd className="key">{key}</kbd>
                      {keyIndex < shortcut.keys.length - 1 && (
                        <span className="key-separator">+</span>
                      )}
                    </React.Fragment>
                  ))}
                </div>
                <div className="shortcut-description">
                  {shortcut.description}
                </div>
              </div>
            ))}
          </div>

          <div className="shortcuts-footer">
            <p>Press <kbd className="key">Escape</kbd> to close this dialog</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcutHelp;
