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

describe('showErrorToast — class-hierarchy ordering', () => {
  it('AuthenticationError dispatches to show401Error even though it extends ApiError', () => {
    const fake = new FakeNotificationService();
    showErrorToast(new AuthenticationError(), fake);
    expect(fake.calls.map(c => c.method)).toEqual(['show401Error']);
  });

  it('AuthorizationError dispatches to show403Error even though it extends ApiError', () => {
    const fake = new FakeNotificationService();
    showErrorToast(new AuthorizationError(), fake);
    expect(fake.calls.map(c => c.method)).toEqual(['show403Error']);
  });

  it('Plain ApiError (not a subclass) dispatches to showApiError', () => {
    const fake = new FakeNotificationService();
    showErrorToast(new ApiError(404, 'not found'), fake);
    expect(fake.calls.map(c => c.method)).toEqual(['showApiError']);
  });
});

describe('showErrorToast — edge cases', () => {
  it('null → showError("Unexpected error")', () => {
    const fake = new FakeNotificationService();
    showErrorToast(null, fake);
    expect(fake.calls).toEqual([{ method: 'showError', args: ['Unexpected error', undefined] }]);
  });

  it('undefined → showError("Unexpected error")', () => {
    const fake = new FakeNotificationService();
    showErrorToast(undefined, fake);
    expect(fake.calls).toEqual([{ method: 'showError', args: ['Unexpected error', undefined] }]);
  });

  it('plain object that looks like an error → showError("Unexpected error")', () => {
    const fake = new FakeNotificationService();
    showErrorToast({ message: 'looks like an error', name: 'FakeError' }, fake);
    expect(fake.calls).toEqual([{ method: 'showError', args: ['Unexpected error', undefined] }]);
  });

  it('TypeError (Error subclass not in our hierarchy) → showError(message)', () => {
    const fake = new FakeNotificationService();
    showErrorToast(new TypeError('cannot read property of undefined'), fake);
    expect(fake.calls).toEqual([
      { method: 'showError', args: ['cannot read property of undefined', undefined] },
    ]);
  });

  it('ApiError with empty message → showApiError(status, "")', () => {
    const fake = new FakeNotificationService();
    showErrorToast(new ApiError(503, ''), fake);
    expect(fake.calls).toEqual([{ method: 'showApiError', args: [503, '', undefined] }]);
  });

  it('ApiError 429 → routes through showApiError (no special handling in errorHandler)', () => {
    const fake = new FakeNotificationService();
    showErrorToast(new ApiError(429, 'Too many requests'), fake);
    expect(fake.calls).toEqual([
      { method: 'showApiError', args: [429, 'Too many requests', undefined] },
    ]);
  });

  it('multiple sequential dispatches accumulate on the same fake', () => {
    const fake = new FakeNotificationService();
    showErrorToast(new AuthenticationError(), fake);
    showErrorToast(new NetworkError(), fake);
    showErrorToast(new ApiError(500, 'fail'), fake);
    expect(fake.calls.map(c => c.method)).toEqual([
      'show401Error',
      'showNetworkError',
      'showApiError',
    ]);
  });
});
