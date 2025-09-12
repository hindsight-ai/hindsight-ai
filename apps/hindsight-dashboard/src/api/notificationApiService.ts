/**
 * Notification API Service
 * 
 * Handles all API calls related to notifications and user preferences.
 * Follows the same patterns as existing services (authService, organizationService).
 */

// Use the same base URL pattern as other services
let API_BASE_URL: string = '/api';
try {
  if (typeof window !== 'undefined' && (window as any).__ENV__?.HINDSIGHT_SERVICE_API_URL) {
    API_BASE_URL = (window as any).__ENV__.HINDSIGHT_SERVICE_API_URL;
  } else if (typeof process !== 'undefined' && process.env?.VITE_HINDSIGHT_SERVICE_API_URL) {
    API_BASE_URL = process.env.VITE_HINDSIGHT_SERVICE_API_URL;
  }
} catch {}

const isGuest = (): boolean => {
  try { return sessionStorage.getItem('GUEST_MODE') === 'true'; } catch { return false; }
};

const base = () => {
  const relativeUrl = isGuest() ? '/guest-api' : API_BASE_URL;
  
  let absoluteUrl;
  if (typeof window !== 'undefined') {
    const currentOrigin = window.location.origin;
    const isDev = currentOrigin.includes(':3000');
    
    if (isDev) {
      absoluteUrl = `http://localhost:3000${relativeUrl}`;
    } else {
      absoluteUrl = `${currentOrigin}${relativeUrl}`;
    }
  } else {
    absoluteUrl = relativeUrl;
  }
  
  return absoluteUrl;
};

// TypeScript interfaces for notification data
export interface Notification {
  id: string;
  user_id: string;
  event_type: string;
  title: string;
  message: string;
  action_url?: string;
  action_text?: string;
  metadata?: Record<string, any>;
  is_read: boolean;
  read_at?: string;
  created_at: string;
  expires_at?: string;
}

export interface NotificationListResponse {
  notifications: Notification[];
  unread_count: number;
  total_count: number;
}

export interface NotificationStatsResponse {
  unread_count: number;
  total_notifications: number;
  recent_notifications: Notification[];
}

export interface NotificationPreferences {
  [event_type: string]: {
    email_enabled: boolean;
    in_app_enabled: boolean;
  };
}

export interface NotificationPreferencesResponse {
  preferences: NotificationPreferences;
}

export interface UserNotificationPreference {
  id: string;
  user_id: string;
  event_type: string;
  email_enabled: boolean;
  in_app_enabled: boolean;
  created_at: string;
  updated_at: string;
}

// API Error handling
class NotificationApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'NotificationApiError';
  }
}

const handleResponse = async (response: Response) => {
  if (!response.ok) {
    const text = await response.text();
    throw new NotificationApiError(response.status, text || `HTTP ${response.status}`);
  }
  
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return response.text();
};

// Notification API methods
const notificationApiService = {
  /**
   * Get notifications for the current user
   */
  async getNotifications(unreadOnly: boolean = false, limit: number = 50): Promise<NotificationListResponse> {
    if (isGuest()) {
      // Guest users don't have notifications
      return { notifications: [], unread_count: 0, total_count: 0 };
    }

    const params = new URLSearchParams({
      unread_only: unreadOnly.toString(),
      limit: limit.toString()
    });

    const response = await fetch(`${base()}/notifications?${params}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include'
    });

    return handleResponse(response);
  },

  /**
   * Mark a notification as read
   */
  async markNotificationRead(notificationId: string): Promise<void> {
    if (isGuest()) return;

    const response = await fetch(`${base()}/notifications/${notificationId}/read`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include'
    });

    if (!response.ok) {
      throw new NotificationApiError(response.status, 'Failed to mark notification as read');
    }
  },

  /**
   * Get notification statistics for the current user
   */
  async getNotificationStats(): Promise<NotificationStatsResponse> {
    if (isGuest()) {
      return { unread_count: 0, total_notifications: 0, recent_notifications: [] };
    }

    const response = await fetch(`${base()}/notifications/stats`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include'
    });

    return handleResponse(response);
  },

  /**
   * Get notification preferences for the current user
   */
  async getNotificationPreferences(): Promise<NotificationPreferencesResponse> {
    if (isGuest()) {
      // Return default preferences for guest users
      return {
        preferences: {
          org_invitation: { email_enabled: true, in_app_enabled: true },
          org_membership_added: { email_enabled: true, in_app_enabled: true },
          org_membership_removed: { email_enabled: true, in_app_enabled: true },
          org_role_changed: { email_enabled: true, in_app_enabled: true },
          org_invitation_accepted: { email_enabled: true, in_app_enabled: true },
          org_invitation_declined: { email_enabled: false, in_app_enabled: true }
        }
      };
    }

    const response = await fetch(`${base()}/notifications/preferences`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include'
    });

    return handleResponse(response);
  },

  /**
   * Update notification preference for a specific event type
   */
  async updateNotificationPreference(
    eventType: string, 
    emailEnabled?: boolean, 
    inAppEnabled?: boolean
  ): Promise<UserNotificationPreference> {
    if (isGuest()) {
      throw new NotificationApiError(403, 'Guest users cannot modify preferences');
    }

    const updateData: any = {};
    if (emailEnabled !== undefined) updateData.email_enabled = emailEnabled;
    if (inAppEnabled !== undefined) updateData.in_app_enabled = inAppEnabled;

    const response = await fetch(`${base()}/notifications/preferences/${eventType}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(updateData)
    });

    return handleResponse(response);
  },

  /**
   * Create a test notification (for development/testing)
   */
  async createTestNotification(notificationData: {
    event_type: string;
    title: string;
    message: string;
    action_url?: string;
    action_text?: string;
    metadata?: Record<string, any>;
    expires_days?: number;
  }): Promise<Notification> {
    if (isGuest()) {
      throw new NotificationApiError(403, 'Guest users cannot create notifications');
    }

    const response = await fetch(`${base()}/notifications/test/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(notificationData)
    });

    return handleResponse(response);
  }
};

export default notificationApiService;
