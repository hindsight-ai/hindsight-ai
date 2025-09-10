import React, { useState, useEffect } from 'react';
import { NotificationType } from '../services/notificationService';

interface NotificationProps {
  message: string;
  type?: NotificationType;
  duration?: number;
  onRefresh?: () => void;
  onClose?: () => void;
}

const Notification: React.FC<NotificationProps> = ({ message, type = 'error', duration = 30000, onRefresh, onClose }) => {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => { setIsVisible(false); onClose?.(); }, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  if (!isVisible) return null;

  return (
    <div className={`notification notification-${type}`}>
      <div className="notification-content">
        <span className="notification-message">{message}</span>
        <div className="notification-actions">
          {onRefresh && (
            <button className="notification-button refresh-button" onClick={() => { setIsVisible(false); onRefresh(); }}>
              Refresh Authentication
            </button>
          )}
          <button className="notification-button close-button" onClick={() => { setIsVisible(false); onClose?.(); }}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default Notification;
