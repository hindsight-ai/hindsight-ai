import notificationService from '../notificationService';

describe('notificationService', () => {
  test('debounces identical notifications within debounceDelay', () => {
    // Make debounce smaller for test speed
    notificationService.debounceDelay = 100;
    const id1 = notificationService.showError('Same message');
    const id2 = notificationService.showError('Same message');
    expect(id1).toBeTruthy();
    expect(id2).toBeNull();
    expect(notificationService.getNotifications().length).toBe(1);
  });

  test('different messages are both added', () => {
    notificationService.clearAll();
    const id1 = notificationService.showError('Message A');
    const id2 = notificationService.showError('Message B');
    expect(id1).toBeTruthy();
    expect(id2).toBeTruthy();
    expect(notificationService.getNotifications().length).toBe(2);
  });
});

