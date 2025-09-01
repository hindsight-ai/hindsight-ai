import React, { useState, useEffect } from 'react';

const Notification = ({ message, type = 'error', duration = 30000, onRefresh, onClose }) => {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      if (onClose) onClose();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  if (!isVisible) return null;

  return (
    <div className={`notification notification-${type}`}>
      <div className="notification-content">
        <span className="notification-message">{message}</span>
        <div className="notification-actions">
          <button 
            className="notification-button refresh-button"
            onClick={() => {
              setIsVisible(false);
              if (onRefresh) onRefresh();
            }}
          >
            Refresh Authentication
          </button>
          <button 
            className="notification-button close-button"
            onClick={() => {
              setIsVisible(false);
              if (onClose) onClose();
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default Notification;
