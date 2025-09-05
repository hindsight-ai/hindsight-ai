import React, { useState, useEffect } from 'react';
import Notification from './Notification';
import notificationService from '../services/notificationService';

const NotificationContainer = () => {
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    // Listen for notification changes
    const handleNotificationsChange = (updatedNotifications) => {
      setNotifications(updatedNotifications);
    };

    notificationService.addListener(handleNotificationsChange);

    // Initialize with current notifications
    setNotifications(notificationService.getNotifications());

    // Cleanup listener on unmount
    return () => {
      notificationService.removeListener(handleNotificationsChange);
    };
  }, []);

  const handleRemoveNotification = (id) => {
    notificationService.removeNotification(id);
  };

  return (
    <div className="notification-container">
      {notifications.slice().reverse().map((notification, index) => (
        <div
          key={notification.id}
          className="notification-wrapper"
          style={{
            position: 'relative',
            zIndex: 10000 - index, // Higher z-index for newer notifications
            marginBottom: index < notifications.length - 1 ? '10px' : '0'
          }}
        >
          <Notification
            message={notification.message}
            type={notification.type}
            duration={notification.duration}
            onRefresh={notification.onRefresh}
            onClose={() => handleRemoveNotification(notification.id)}
          />
        </div>
      ))}
    </div>
  );
};

export default NotificationContainer;
