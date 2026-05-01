export type NotificationType = 'success' | 'info' | 'warning' | 'error';

export interface NotificationItem {
  id: number;
  type: NotificationType;
  message: string;
  duration?: number;
  onRefresh?: () => void;
}

export type NotificationListener = (notifications: NotificationItem[]) => void;

export interface INotificationService {
  addNotification(notification: Omit<NotificationItem, 'id'>): number | null;
  removeNotification(id: number): void;
  getNotifications(): NotificationItem[];
  clearAll(): void;
  addListener(callback: NotificationListener): void;
  removeListener(callback: NotificationListener): void;

  show401Error(): number | null;
  show403Error(action?: string): number | null;
  show404Error(resource?: string): number | null;
  show500Error(): number | null;
  showNetworkError(): number | null;
  showApiError(status: number, message?: string, action?: string): number | null;

  showSuccess(message: string, duration?: number): number | null;
  showInfo(message: string, duration?: number): number | null;
  showWarning(message: string, duration?: number): number | null;
  showError(message: string, duration?: number): number | null;
}
