import React, { useState, useRef, useEffect } from 'react';

interface Option {
  value: string;
  label: string;
}

interface MultiSelectDropdownProps {
  options: Option[];
  selectedValues: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  'data-testid'?: string;
}

const MultiSelectDropdown: React.FC<MultiSelectDropdownProps> = ({ options, selectedValues, onChange, placeholder, 'data-testid': dataTestId }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const headerRef = useRef(null);
  const optionsRef = useRef([]); // To hold refs to individual options

  const handleToggle = () => {
    setIsOpen((prevIsOpen) => !prevIsOpen);
  };

  const handleOptionClick = (value) => {
    const newSelectedValues = selectedValues.includes(value)
      ? selectedValues.filter((v) => v !== value)
      : [...selectedValues, value];
    onChange(newSelectedValues);
    // Keep dropdown open after selection for multi-select behavior
  };

  const handleClickOutside = (event) => {
    if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
      setIsOpen(false);
    }
  };

  const handleHeaderKeyDown = (event) => {
    switch (event.key) {
      case 'Enter':
      case ' ':
        event.preventDefault();
        handleToggle();
        break;
      case 'ArrowDown':
        event.preventDefault();
        if (!isOpen) {
          setIsOpen(true);
        }
        // Move focus to the first option if dropdown is open or just opened
        if (optionsRef.current.length > 0) {
          optionsRef.current[0].focus();
        }
        break;
      default:
        break;
    }
  };

  const handleOptionKeyDown = (event, index, value) => {
    switch (event.key) {
      case 'Enter':
      case ' ':
        event.preventDefault();
        handleOptionClick(value);
        break;
      case 'ArrowUp':
        event.preventDefault();
        if (index > 0) {
          optionsRef.current[index - 1].focus();
        } else {
          // If at first option, loop to last or go back to header
          headerRef.current.focus();
        }
        break;
      case 'ArrowDown':
        event.preventDefault();
        if (index < optionsRef.current.length - 1) {
          optionsRef.current[index + 1].focus();
        } else {
          // If at last option, loop to first or stay
          optionsRef.current[0].focus();
        }
        break;
      case 'Escape':
        event.preventDefault();
        setIsOpen(false);
        headerRef.current.focus(); // Return focus to header
        break;
      default:
        break;
    }
  };

  useEffect(() => {
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  useEffect(() => {
    if (isOpen && optionsRef.current.length > 0) {
      // Focus the first selected option, or the first option if none are selected
      const firstSelectedOptionIndex = options.findIndex(option => selectedValues.includes(option.value));
      if (firstSelectedOptionIndex !== -1 && optionsRef.current[firstSelectedOptionIndex]) {
        optionsRef.current[firstSelectedOptionIndex].focus();
      } else if (optionsRef.current[0]) {
        optionsRef.current[0].focus();
      }
    }
  }, [isOpen, options, selectedValues]);


  const handleRemoveTag = (valueToRemove) => {
    const newSelectedValues = selectedValues.filter((v) => v !== valueToRemove);
    onChange(newSelectedValues);
  };

  const dropdownOptionsId = `multi-select-dropdown-options-${Math.random().toString(36).substr(2, 9)}`; // Unique ID

  return (
    <div className="multi-select-dropdown" ref={dropdownRef} data-testid={dataTestId}>
      <div
        className="dropdown-header"
        onClick={handleToggle}
        onKeyDown={handleHeaderKeyDown}
        tabIndex="0"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={dropdownOptionsId}
        ref={headerRef}
      >
        {selectedValues.length > 0 ? (
          <div className="selected-tags">
            {selectedValues.map((value) => {
              const option = options.find((opt) => opt.value === value);
              return (
                <span key={value} className="selected-tag">
                  {option ? option.label : value}
                  <button
                    type="button"
                    className="remove-tag-button"
                    onClick={(e) => {
                      e.stopPropagation(); // Prevent dropdown from toggling
                      handleRemoveTag(value);
                    }}
                    aria-label={`Remove ${option ? option.label : value}`}
                  >
                    &times;
                  </button>
                </span>
              );
            })}
          </div>
        ) : (
          <span className="selected-values-placeholder">{placeholder}</span>
        )}
        <span className="dropdown-arrow">{isOpen ? '▲' : '▼'}</span>
      </div>
      {isOpen && (
        <div
          id={dropdownOptionsId}
          className="dropdown-options"
          role="listbox"
          aria-multiselectable="true"
        >
          {options.length > 0 ? (
            options.map((option, index) => (
              <div
                key={option.value}
                className={`dropdown-option ${selectedValues.includes(option.value) ? 'selected' : ''}`}
                onClick={() => handleOptionClick(option.value)}
                onKeyDown={(e) => handleOptionKeyDown(e, index, option.value)}
                tabIndex="-1" // Programmatically manage focus
                role="option"
                aria-selected={selectedValues.includes(option.value)}
                ref={(el) => (optionsRef.current[index] = el)}
              >
                {option.label}
              </div>
            ))
          ) : (
            <div className="dropdown-empty-message" role="alert">
              No options available.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MultiSelectDropdown;
