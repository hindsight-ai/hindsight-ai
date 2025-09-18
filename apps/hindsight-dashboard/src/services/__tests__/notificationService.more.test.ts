import notificationService from '../notificationService';

describe('notificationService convenience + listeners', () => {
  beforeEach(() => {
    notificationService.clearAll();
    notificationService.debounceDelay = 10;
  });

  test('show401Error adds error and onRefresh updates location', () => {
    // Provide a custom location with href setter to capture redirects
    const hrefSet = jest.fn();
    Object.defineProperty(window, 'location', {
      value: {
        pathname: '/here',
        search: '?x=1',
        hash: '#h',
        set href(v) { hrefSet(v); },
      },
      writable: true,
    });
    const id = notificationService.show401Error();
    expect(id).toBeTruthy();
    const [n] = notificationService.getNotifications();
    expect(n.type).toBe('error');
    n.onRefresh();
    expect(hrefSet).toHaveBeenCalledWith(expect.stringContaining('/oauth2/sign_in?rd='));
  });

  test('success/info/warning/error helpers add notifications', () => {
    const ids = [
      notificationService.showSuccess('ok'),
      notificationService.showInfo('info'),
      notificationService.showWarning('warn'),
      notificationService.showError('err'),
    ];
    expect(ids.every(Boolean)).toBe(true);
    const types = notificationService.getNotifications().map(n => n.type).sort();
    expect(types).toEqual(['error','info','success','warning']);
  });

  test('removeNotification and clearAll notify listeners', () => {
    const events = [];
    const listener = (list) => events.push(list.length);
    notificationService.addListener(listener);
    const id1 = notificationService.showInfo('a');
    const id2 = notificationService.showInfo('b');
    notificationService.removeNotification(id1);
    notificationService.clearAll();
    notificationService.removeListener(listener);
    // events: after add a (1), add b (2), remove (1), clear (0)
    expect(events).toEqual([1,2,1,0]);
  });

  test('cleanupOldEntries prunes stale lastNotificationTimes', () => {
    const now = Date.now();
    notificationService.debounceDelay = 100;
    // Seed a key with old time
    notificationService.lastNotificationTimes.set('k', now - 1000);
    notificationService.cleanupOldEntries(now);
    expect(notificationService.lastNotificationTimes.has('k')).toBe(false);
  });
});
