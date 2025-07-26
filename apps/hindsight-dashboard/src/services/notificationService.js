class NotificationService {
  constructor() {
    this.notifications = [];
    this.listeners = [];
    this.lastNotificationTime = 0;
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
    this.lastNotificationTime = now;
    this.notifyListeners();
    return id;
  }

  // Determine if we should debounce a notification
  shouldDebounceNotification(notification, currentTime) {
    // Always show error notifications (like 401 errors)
    if (notification.type === 'error') {
      return false;
    }
    
    // Debounce if too much time hasn't passed since last notification
    return (currentTime - this.lastNotificationTime) < this.debounceDelay;
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
        window.location.href = 'https://auth.hindsight-ai.com/oauth2/sign_in?rd=https%3A%2F%2Fdashboard.hindsight-ai.com';
      }
    });
  }
}

// Create singleton instance
const notificationService = new NotificationService();

// Export singleton instance
export default notificationService;
