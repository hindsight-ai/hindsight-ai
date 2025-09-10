export type NotificationType = 'success' | 'info' | 'warning' | 'error';

export interface NotificationItem {
  id: number;
  type: NotificationType;
  message: string;
  duration?: number;
  onRefresh?: () => void;
}

type Listener = (notifications: NotificationItem[]) => void;

class NotificationService {
  private notifications: NotificationItem[] = [];
  private listeners: Listener[] = [];
  private lastNotificationTimes: Map<string, number> = new Map();
  private debounceDelay = 5000; // ms

  addNotification(notification: Omit<NotificationItem, 'id'>): number | null {
    const now = Date.now();
    if (this.shouldDebounceNotification(notification, now)) return null;
    const id = now + Math.random();
    const withId: NotificationItem = { ...notification, id };
    this.notifications.push(withId);
    const key = this.getNotificationKey(notification);
    this.lastNotificationTimes.set(key, now);
    this.cleanupOldEntries(now);
    this.notifyListeners();
    return id;
  }

  private cleanupOldEntries(currentTime: number) {
    const cutoff = currentTime - this.debounceDelay * 2;
    for (const [key, time] of this.lastNotificationTimes.entries()) {
      if (time < cutoff) this.lastNotificationTimes.delete(key);
    }
  }

  private getNotificationKey(notification: Omit<NotificationItem, 'id'>): string {
    const messageKey = notification.message ? notification.message.substring(0, 50) : '';
    return `${notification.type || 'info'}_${messageKey}`;
  }

  private shouldDebounceNotification(notification: Omit<NotificationItem, 'id'>, currentTime: number): boolean {
    const key = this.getNotificationKey(notification);
    const last = this.lastNotificationTimes.get(key) || 0;
    return currentTime - last < this.debounceDelay;
  }

  removeNotification(id: number) {
    this.notifications = this.notifications.filter(n => n.id !== id);
    this.notifyListeners();
  }

  getNotifications(): NotificationItem[] {
    return [...this.notifications];
  }

  clearAll() {
    this.notifications = [];
    this.notifyListeners();
  }

  addListener(callback: Listener) { this.listeners.push(callback); }
  removeListener(callback: Listener) { this.listeners = this.listeners.filter(l => l !== callback); }
  private notifyListeners() { this.listeners.forEach(cb => cb(this.getNotifications())); }

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

  showSuccess(message: string, duration = 5000) { return this.addNotification({ type: 'success', message, duration }); }
  showInfo(message: string, duration = 5000) { return this.addNotification({ type: 'info', message, duration }); }
  showWarning(message: string, duration = 7000) { return this.addNotification({ type: 'warning', message, duration }); }
  showError(message: string, duration = 10000) { return this.addNotification({ type: 'error', message, duration }); }
}

const notificationService = new NotificationService();
export default notificationService;
