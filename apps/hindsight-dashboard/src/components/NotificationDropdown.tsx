/**
 * Notification Dropdown Component
 * 
 * Dropdown that shows a list of notifications with read/unread states,
 * action buttons, and links to settings.
 */

import React, { useEffect, useState } from 'react';
import { useNotifications } from '../context/NotificationContext';
import { Notification } from '../api/notificationApiService';
import NotificationSettingsModal from './NotificationSettingsModal';

interface NotificationDropdownProps {
  onClose: () => void;
  onNotificationClick: () => void;
}

interface NotificationItemProps {
  notification: Notification;
  onMarkAsRead: (id: string) => void;
  onClick: () => void;
}

const NotificationItem: React.FC<NotificationItemProps> = ({ notification, onMarkAsRead, onClick }) => {
  const handleClick = () => {
    if (!notification.is_read) {
      onMarkAsRead(notification.id);
    }
    onClick();
    
    // If notification has an action URL, navigate to it
    if (notification.action_url) {
      // For internal URLs, use router navigation
      if (notification.action_url.startsWith('/')) {
        window.location.href = notification.action_url;
      } else {
        // For external URLs, open in new tab
        window.open(notification.action_url, '_blank', 'noopener,noreferrer');
      }
    }
  };

  const formatTimeAgo = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMs = now.getTime() - date.getTime();
    const diffInMins = Math.floor(diffInMs / (1000 * 60));
    const diffInHours = Math.floor(diffInMins / 60);
    const diffInDays = Math.floor(diffInHours / 24);

    if (diffInMins < 1) return 'Just now';
    if (diffInMins < 60) return `${diffInMins}m ago`;
    if (diffInHours < 24) return `${diffInHours}h ago`;
    if (diffInDays < 7) return `${diffInDays}d ago`;
    
    return date.toLocaleDateString();
  };

  return (
    <div
      onClick={handleClick}
      className={`
        p-3 border-b border-gray-100 last:border-b-0 cursor-pointer
        hover:bg-gray-50 transition-colors duration-150
        ${!notification.is_read ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''}
      `}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          {/* Title */}
          <div className={`text-sm font-medium text-gray-900 truncate ${!notification.is_read ? 'font-semibold' : ''}`}>
            {notification.title}
          </div>
          
          {/* Message */}
          <div className="text-xs text-gray-600 mt-1 line-clamp-2">
            {notification.message}
          </div>
          
          {/* Action button */}
          {notification.action_text && notification.action_url && (
            <div className="mt-2">
              <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded">
                {notification.action_text}
              </span>
            </div>
          )}
          
          {/* Timestamp */}
          <div className="text-xs text-gray-400 mt-1">
            {formatTimeAgo(notification.created_at)}
          </div>
        </div>
        
        {/* Unread indicator */}
        {!notification.is_read && (
          <div className="w-2 h-2 bg-blue-500 rounded-full mt-1 flex-shrink-0"></div>
        )}
      </div>
    </div>
  );
};

const NotificationDropdown: React.FC<NotificationDropdownProps> = ({ onClose, onNotificationClick }) => {
  const { notifications, unreadCount, loading, markAsRead, refreshNotifications } = useNotifications();
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);

  // Refresh notifications when dropdown opens
  useEffect(() => {
    refreshNotifications();
  }, [refreshNotifications]);

  const handleMarkAsRead = async (notificationId: string) => {
    try {
      await markAsRead(notificationId);
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  };

  const handleMarkAllAsRead = async () => {
    const unreadNotifications = notifications.filter(n => !n.is_read);
    
    // Mark all unread notifications as read
    const promises = unreadNotifications.map(notification => 
      markAsRead(notification.id).catch(error => {
        console.error(`Failed to mark notification ${notification.id} as read:`, error);
      })
    );
    
    await Promise.all(promises);
  };

  const handleSettingsClick = () => {
    setSettingsModalOpen(true);
  };

  return (
    <>
      <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50 max-h-96 flex flex-col">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">
            Notifications
            {unreadCount > 0 && (
              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                {unreadCount} new
              </span>
            )}
          </h3>
          
          <div className="flex items-center gap-2">
            {/* Mark all as read button */}
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllAsRead}
                className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                disabled={loading}
              >
                Mark all read
              </button>
            )}
            
            {/* Settings button */}
            <button
              onClick={handleSettingsClick}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              title="Notification settings"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Notification List */}
        <div className="flex-1 overflow-y-auto">
          {loading && notifications.length === 0 ? (
            <div className="p-4 text-center">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-sm text-gray-500 mt-2">Loading notifications...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-8 text-center">
              <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              <p className="text-sm text-gray-500">No notifications yet</p>
              <p className="text-xs text-gray-400 mt-1">We'll notify you about important updates</p>
            </div>
          ) : (
            <div>
              {notifications.map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onMarkAsRead={handleMarkAsRead}
                  onClick={onNotificationClick}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {notifications.length > 0 && (
          <div className="px-4 py-3 border-t border-gray-100 bg-gray-50 rounded-b-lg">
            <button
              onClick={() => {
                onClose();
                // TODO: Navigate to full notifications page
                console.log('View all notifications');
              }}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium w-full text-center"
            >
              View all notifications
            </button>
          </div>
        )}
      </div>

      {/* Settings Modal */}
      <NotificationSettingsModal
        isOpen={settingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
      />
    </>
  );
};

export default NotificationDropdown;
