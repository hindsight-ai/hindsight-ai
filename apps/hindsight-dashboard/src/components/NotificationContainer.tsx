import React, { useState, useEffect } from 'react';
import Notification from './Notification';
import notificationService, { NotificationItem } from '../services/notificationService';

const NotificationContainer: React.FC = () => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  useEffect(() => {
    const handleChange = (updated: NotificationItem[]) => setNotifications(updated);
    notificationService.addListener(handleChange);
    setNotifications(notificationService.getNotifications());
    return () => notificationService.removeListener(handleChange);
  }, []);

  return (
    <div className="notification-container">
      {notifications.map((n, index) => (
        <div key={n.id} className="notification-wrapper" style={{ zIndex: 99999 - index }}>
          <Notification message={n.message} type={n.type} duration={n.duration} onRefresh={n.onRefresh} onClose={() => notificationService.removeNotification(n.id)} />
        </div>
      ))}
    </div>
  );
};

export default NotificationContainer;
