/**
 * Contract test for the INotificationService interface introduced in #79.
 *
 * Goal: catch regressions where the singleton is mistakenly typed/exported
 * in a way that breaks the interface contract — e.g. a method removed from
 * the class but still declared on the interface, or vice versa.
 *
 * The other notificationService tests probe internal/private state
 * (debounce, dedup) using `as any` casts. This file is the boundary check.
 */

import notificationService from '../notificationService';
import type {
  INotificationService,
  NotificationItem,
  NotificationListener,
  NotificationType,
} from '../notificationService.types';

describe('notificationService — INotificationService contract', () => {
  beforeEach(() => {
    notificationService.clearAll();
  });

  const requiredMethods: Array<keyof INotificationService> = [
    'addNotification',
    'removeNotification',
    'getNotifications',
    'clearAll',
    'addListener',
    'removeListener',
    'show401Error',
    'show403Error',
    'show404Error',
    'show500Error',
    'showNetworkError',
    'showApiError',
    'showSuccess',
    'showInfo',
    'showWarning',
    'showError',
  ];

  it('singleton exposes every interface method as a function', () => {
    for (const method of requiredMethods) {
      expect(typeof (notificationService as INotificationService)[method]).toBe('function');
    }
  });

  it('singleton is structurally assignable to INotificationService', () => {
    // If this test compiles, the contract holds at the type level.
    const ref: INotificationService = notificationService;
    expect(ref).toBe(notificationService);
  });

  it('through the interface — addNotification → getNotifications → removeNotification lifecycle', () => {
    const ref: INotificationService = notificationService;

    const id = ref.addNotification({ type: 'info', message: 'contract-test-1' });
    expect(typeof id).toBe('number');

    const items = ref.getNotifications();
    expect(items.some((n) => n.message === 'contract-test-1')).toBe(true);

    ref.removeNotification(id as number);
    expect(ref.getNotifications().some((n) => n.id === id)).toBe(false);
  });

  it('through the interface — addListener fires on changes; removeListener stops fires', () => {
    const ref: INotificationService = notificationService;
    const events: NotificationItem[][] = [];
    const listener: NotificationListener = (n) => events.push([...n]);

    ref.addListener(listener);
    ref.addNotification({ type: 'success', message: 'contract-test-listener' });
    expect(events.length).toBeGreaterThan(0);

    const before = events.length;
    ref.removeListener(listener);
    ref.addNotification({ type: 'info', message: 'after-remove' });
    expect(events.length).toBe(before);
  });

  it('through the interface — clearAll empties getNotifications', () => {
    const ref: INotificationService = notificationService;
    ref.addNotification({ type: 'error', message: 'contract-test-clear-1' });
    ref.addNotification({ type: 'warning', message: 'contract-test-clear-2' });
    expect(ref.getNotifications().length).toBeGreaterThan(0);

    ref.clearAll();
    expect(ref.getNotifications()).toEqual([]);
  });

  it('through the interface — every show*() helper produces a notification of the right type', () => {
    const ref: INotificationService = notificationService;
    const cases: Array<[() => number | null, NotificationType, RegExp | string]> = [
      [() => ref.show401Error(), 'error', /Authentication/],
      [() => ref.show403Error('do thing'), 'error', /Permission denied/],
      [() => ref.show404Error('thing'), 'error', /not found/],
      [() => ref.show500Error(), 'error', /Server error/],
      [() => ref.showNetworkError(), 'error', /Network/],
      [() => ref.showSuccess('ok'), 'success', 'ok'],
      [() => ref.showInfo('info'), 'info', 'info'],
      [() => ref.showWarning('warn'), 'warning', 'warn'],
      [() => ref.showError('err'), 'error', 'err'],
    ];
    for (const [fire, type, matcher] of cases) {
      ref.clearAll();
      const id = fire();
      expect(typeof id).toBe('number');
      const item = ref.getNotifications().find((n) => n.id === id);
      expect(item).toBeDefined();
      expect(item!.type).toBe(type);
      if (matcher instanceof RegExp) {
        expect(item!.message).toMatch(matcher);
      } else {
        expect(item!.message).toContain(matcher);
      }
    }
  });

  it('showApiError dispatches to show401Error on status 401', () => {
    const ref: INotificationService = notificationService;
    ref.clearAll();
    ref.showApiError(401);
    const items = ref.getNotifications();
    expect(items.length).toBe(1);
    expect(items[0].message).toMatch(/Authentication/);
  });

  it('showApiError dispatches to show403Error on status 403', () => {
    const ref: INotificationService = notificationService;
    ref.clearAll();
    ref.showApiError(403, 'forbidden', 'create org');
    const items = ref.getNotifications();
    expect(items.length).toBe(1);
    expect(items[0].message).toMatch(/Permission denied/);
    expect(items[0].message).toContain('create org');
  });
});
