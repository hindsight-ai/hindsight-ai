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
      {notifications.map(notification => (
        <Notification
          key={notification.id}
          message={notification.message}
          type={notification.type}
          duration={notification.duration}
          onRefresh={notification.onRefresh}
          onClose={() => handleRemoveNotification(notification.id)}
        />
      ))}
    </div>
  );
};

export default NotificationContainer;
