class NotificationService {
  constructor() {
    this.notifications = [];
    this.listeners = [];
  }

  // Add a notification
  addNotification(notification) {
    const id = Date.now() + Math.random();
    const notificationWithId = { ...notification, id };
    this.notifications.push(notificationWithId);
    this.notifyListeners();
    return id;
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
