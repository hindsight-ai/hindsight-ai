/**
 * Notification Context
 * 
 * Provides centralized state management for notifications and preferences.
 * Follows the same pattern as AuthContext and OrganizationContext.
 */

import React, { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react';
import notificationApiService, { 
  Notification, 
  NotificationPreferences,
  NotificationListResponse,
  NotificationStatsResponse 
} from '../api/notificationApiService';
import { useAuth } from './AuthContext';

interface NotificationContextValue {
  // Notification data
  notifications: Notification[];
  unreadCount: number;
  loading: boolean;
  
  // Preferences
  preferences: NotificationPreferences | null;
  preferencesLoading: boolean;
  
  // Actions
  refreshNotifications: () => Promise<void>;
  markAsRead: (notificationId: string) => Promise<void>;
  updatePreference: (eventType: string, emailEnabled?: boolean, inAppEnabled?: boolean) => Promise<void>;
  
  // Real-time updates
  lastUpdated: Date | null;
}

const NotificationContext = createContext<NotificationContextValue | undefined>(undefined);

export const NotificationProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const { user, guest } = useAuth();
  
  // Notification state
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  
  // Preferences state
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);
  const [preferencesLoading, setPreferencesLoading] = useState<boolean>(false);

  /**
   * Refresh notifications from the API
   */
  const refreshNotifications = useCallback(async () => {
    if (guest || !user?.authenticated) {
      setNotifications([]);
      setUnreadCount(0);
      setLastUpdated(new Date());
      return;
    }

    try {
      setLoading(true);
      const response: NotificationListResponse = await notificationApiService.getNotifications(false, 50);
      setNotifications(response.notifications);
      setUnreadCount(response.unread_count);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to refresh notifications:', error);
      // Don't clear existing notifications on error - just log it
    } finally {
      setLoading(false);
    }
  }, [guest, user?.authenticated]);

  /**
   * Load user notification preferences
   */
  const loadPreferences = useCallback(async () => {
    if (guest || !user?.authenticated) {
      // Set default preferences for guest users
      setPreferences({
        org_invitation: { email_enabled: true, in_app_enabled: true },
        org_membership_added: { email_enabled: true, in_app_enabled: true },
        org_membership_removed: { email_enabled: true, in_app_enabled: true },
        org_role_changed: { email_enabled: true, in_app_enabled: true },
        org_invitation_accepted: { email_enabled: true, in_app_enabled: true },
        org_invitation_declined: { email_enabled: false, in_app_enabled: true }
      });
      return;
    }

    try {
      setPreferencesLoading(true);
      const response = await notificationApiService.getNotificationPreferences();
      setPreferences(response.preferences);
    } catch (error) {
      console.error('Failed to load notification preferences:', error);
    } finally {
      setPreferencesLoading(false);
    }
  }, [guest, user?.authenticated]);

  /**
   * Mark a notification as read
   */
  const markAsRead = useCallback(async (notificationId: string) => {
    if (guest || !user?.authenticated) return;

    try {
      await notificationApiService.markNotificationRead(notificationId);
      
      // Optimistically update local state
      setNotifications(prev => 
        prev.map(notification => 
          notification.id === notificationId 
            ? { ...notification, is_read: true, read_at: new Date().toISOString() }
            : notification
        )
      );
      
      // Update unread count
      setUnreadCount(prev => Math.max(0, prev - 1));
      
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
      // Refresh notifications to get current state
      refreshNotifications();
    }
  }, [guest, user?.authenticated, refreshNotifications]);

  /**
   * Update a notification preference
   */
  const updatePreference = useCallback(async (
    eventType: string, 
    emailEnabled?: boolean, 
    inAppEnabled?: boolean
  ) => {
    if (guest || !user?.authenticated) return;

    try {
      await notificationApiService.updateNotificationPreference(eventType, emailEnabled, inAppEnabled);
      
      // Optimistically update local state
      setPreferences(prev => {
        if (!prev) return prev;
        
        return {
          ...prev,
          [eventType]: {
            email_enabled: emailEnabled !== undefined ? emailEnabled : prev[eventType]?.email_enabled ?? true,
            in_app_enabled: inAppEnabled !== undefined ? inAppEnabled : prev[eventType]?.in_app_enabled ?? true
          }
        };
      });
      
    } catch (error) {
      console.error('Failed to update notification preference:', error);
      // Refresh preferences to get current state
      loadPreferences();
      throw error; // Re-throw so UI can show error message
    }
  }, [guest, user?.authenticated, loadPreferences]);

  // Load initial data when user changes
  useEffect(() => {
    if (user !== null) { // Only load when we have user data (including guest state)
      refreshNotifications();
      loadPreferences();
    }
  }, [user, refreshNotifications, loadPreferences]);

  // Set up polling for real-time updates
  useEffect(() => {
    if (guest || !user?.authenticated) return;

    // Poll for new notifications every 30 seconds
    const interval = setInterval(() => {
      refreshNotifications();
    }, 30000);

    // Also refresh when the tab becomes visible
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        refreshNotifications();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [guest, user?.authenticated, refreshNotifications]);

  const value = useMemo<NotificationContextValue>(() => ({
    notifications,
    unreadCount,
    loading,
    preferences,
    preferencesLoading,
    refreshNotifications,
    markAsRead,
    updatePreference,
    lastUpdated
  }), [
    notifications,
    unreadCount,
    loading,
    preferences,
    preferencesLoading,
    refreshNotifications,
    markAsRead,
    updatePreference,
    lastUpdated
  ]);

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

/**
 * Hook to use the notification context
 */
export const useNotifications = (): NotificationContextValue => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

export default NotificationContext;
