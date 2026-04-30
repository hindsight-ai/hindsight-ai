import { showErrorToast } from '../errorHandler';
import { ApiError, AuthenticationError, AuthorizationError, NetworkError } from '../errors';
import type {
  INotificationService,
  NotificationItem,
  NotificationListener,
} from '../../services/notificationService.types';

class FakeNotificationService implements INotificationService {
  public calls: Array<{ method: string; args: unknown[] }> = [];

  private record(method: string, ...args: unknown[]): number | null {
    this.calls.push({ method, args });
    return 1;
  }

  addNotification(n: Omit<NotificationItem, 'id'>) { return this.record('addNotification', n); }
  removeNotification(id: number) { this.record('removeNotification', id); }
  getNotifications(): NotificationItem[] { return []; }
  clearAll() { this.record('clearAll'); }
  addListener(cb: NotificationListener) { this.record('addListener', cb); }
  removeListener(cb: NotificationListener) { this.record('removeListener', cb); }

  show401Error() { return this.record('show401Error'); }
  show403Error(action?: string) { return this.record('show403Error', action); }
  show404Error(resource?: string) { return this.record('show404Error', resource); }
  show500Error() { return this.record('show500Error'); }
  showNetworkError() { return this.record('showNetworkError'); }
  showApiError(status: number, message?: string, action?: string) { return this.record('showApiError', status, message, action); }
  showSuccess(message: string, duration?: number) { return this.record('showSuccess', message, duration); }
  showInfo(message: string, duration?: number) { return this.record('showInfo', message, duration); }
  showWarning(message: string, duration?: number) { return this.record('showWarning', message, duration); }
  showError(message: string, duration?: number) { return this.record('showError', message, duration); }
}

describe('showErrorToast — dispatches via INotificationService', () => {
  it('AuthenticationError → show401Error', () => {
    const fake = new FakeNotificationService();
    showErrorToast(new AuthenticationError(), fake);
    expect(fake.calls).toEqual([{ method: 'show401Error', args: [] }]);
  });

  it('AuthorizationError → show403Error', () => {
    const fake = new FakeNotificationService();
    showErrorToast(new AuthorizationError(), fake);
    expect(fake.calls).toEqual([{ method: 'show403Error', args: [undefined] }]);
  });

  it('NetworkError → showNetworkError', () => {
    const fake = new FakeNotificationService();
    showErrorToast(new NetworkError('boom'), fake);
    expect(fake.calls).toEqual([{ method: 'showNetworkError', args: [] }]);
  });

  it('ApiError → showApiError(status, message)', () => {
    const fake = new FakeNotificationService();
    showErrorToast(new ApiError(500, 'boom'), fake);
    expect(fake.calls).toEqual([{ method: 'showApiError', args: [500, 'boom', undefined] }]);
  });

  it('generic Error → showError(message)', () => {
    const fake = new FakeNotificationService();
    showErrorToast(new Error('plain'), fake);
    expect(fake.calls).toEqual([{ method: 'showError', args: ['plain', undefined] }]);
  });

  it('unknown non-Error → showError("Unexpected error")', () => {
    const fake = new FakeNotificationService();
    showErrorToast('not an error', fake);
    expect(fake.calls).toEqual([{ method: 'showError', args: ['Unexpected error', undefined] }]);
  });

  it('defaults to the singleton when no service injected — interface contract holds', () => {
    expect(() => showErrorToast(new Error('default-singleton'))).not.toThrow();
  });
});
