class NotificationService {
  constructor() {
    this.notifications = [];
    this.listeners = [];
    this.lastNotificationTimes = new Map(); // Track last time per notification type/message
    this.debounceDelay = 5000; // 5 seconds default debounce delay
  }

  // Add a notification with debouncing
  addNotification(notification) {
    const now = Date.now();
    
    // Check if we should debounce this notification
    if (this.shouldDebounceNotification(notification, now)) {
      return null; // Skip this notification
    }
    
    const id = now + Math.random();
    const notificationWithId = { ...notification, id };
    this.notifications.push(notificationWithId);
    
    // Update last notification time for this specific notification type/message
    const key = this.getNotificationKey(notification);
    this.lastNotificationTimes.set(key, now);
    
    // Cleanup old entries to prevent memory leaks
    this.cleanupOldEntries(now);
    
    this.notifyListeners();
    return id;
  }

  // Cleanup old notification time entries to prevent memory leaks
  cleanupOldEntries(currentTime) {
    const cutoffTime = currentTime - (this.debounceDelay * 2); // Keep entries for 2x debounce time
    for (const [key, time] of this.lastNotificationTimes.entries()) {
      if (time < cutoffTime) {
        this.lastNotificationTimes.delete(key);
      }
    }
  }

  // Generate a key for identifying similar notifications
  getNotificationKey(notification) {
    // Group by type and message content (truncated for comparison)
    const messageKey = notification.message ? notification.message.substring(0, 50) : '';
    return `${notification.type || 'info'}_${messageKey}`;
  }

  // Determine if we should debounce a notification
  shouldDebounceNotification(notification, currentTime) {
    // Check if similar notification was shown recently
    const key = this.getNotificationKey(notification);
    const lastTime = this.lastNotificationTimes.get(key) || 0;
    
    // Debounce if too much time hasn't passed since last similar notification
    return (currentTime - lastTime) < this.debounceDelay;
  }

  // Remove a notification by ID
  removeNotification(id) {
    this.notifications = this.notifications.filter(notification => notification.id !== id);
    this.notifyListeners();
  }

  // Get all notifications
  getNotifications() {
    return [...this.notifications];
  }

  // Clear all notifications
  clearAll() {
    this.notifications = [];
    this.notifyListeners();
  }

  // Add listener for notification changes
  addListener(callback) {
    this.listeners.push(callback);
  }

  // Remove listener
  removeListener(callback) {
    this.listeners = this.listeners.filter(listener => listener !== callback);
  }

  // Notify all listeners of changes
  notifyListeners() {
    this.listeners.forEach(callback => callback(this.getNotifications()));
  }

  // Show 401 error notification
  show401Error() {
    return this.addNotification({
      type: 'error',
      message: 'Authentication error (401). Your session may have expired. Please refresh authentication to continue.',
      duration: 30000,
      onRefresh: () => {
        const rd = encodeURIComponent(window.location.pathname + window.location.search + window.location.hash);
        window.location.href = `/oauth2/sign_in?rd=${rd}`;
      }
    });
  }

  // Show success notification
  showSuccess(message, duration = 5000) {
    return this.addNotification({
      type: 'success',
      message: message,
      duration: duration
    });
  }

  // Show info notification
  showInfo(message, duration = 5000) {
    return this.addNotification({
      type: 'info',
      message: message,
      duration: duration
    });
  }

  // Show warning notification
  showWarning(message, duration = 7000) {
    return this.addNotification({
      type: 'warning',
      message: message,
      duration: duration
    });
  }

  // Show error notification
  showError(message, duration = 10000) {
    return this.addNotification({
      type: 'error',
      message: message,
      duration: duration
    });
  }
}

// Create singleton instance
const notificationService = new NotificationService();

// Export singleton instance
export default notificationService;
