import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';

// Mock Notification to a simple component for easier assertions
jest.mock('../Notification', () => ({
  __esModule: true,
  default: ({ message, onClose }) => (
    <div data-testid="notification">
      <span>{message}</span>
      <button onClick={onClose}>Close</button>
    </div>
  ),
}));

// Mock notificationService with internal state and helper controls
jest.mock('../../services/notificationService', () => {
  const mockListeners = new Set();
  const mockNotifications = [];
  const api = {
    addListener: (cb) => mockListeners.add(cb),
    removeListener: (cb) => mockListeners.delete(cb),
    getNotifications: () => [...mockNotifications],
    removeNotification: jest.fn((id) => {
      const idx = mockNotifications.findIndex(n => n.id === id);
      if (idx >= 0) mockNotifications.splice(idx, 1);
      mockListeners.forEach(cb => cb([...mockNotifications]));
    }),
  };
  return {
    __esModule: true,
    default: api,
    __mock: {
      setNotifications: (list) => {
        mockNotifications.length = 0;
        mockNotifications.push(...list);
        mockListeners.forEach(cb => cb([...mockNotifications]));
      },
      notify: () => mockListeners.forEach(cb => cb([...mockNotifications])),
    },
  };
});

import NotificationContainer from '../NotificationContainer';
import { __mock as notificationMock } from '../../services/notificationService';

describe('NotificationContainer', () => {
  beforeEach(() => {
    notificationMock.setNotifications([]);
  });

  test('renders notifications from service and supports remove', () => {
    render(<NotificationContainer />);
    act(() => {
      notificationMock.setNotifications([{ id: 1, message: 'Hello' }, { id: 2, message: 'World' }]);
    });
    expect(screen.getAllByTestId('notification')).toHaveLength(2);

    // Remove first notification
    const firstClose = screen.getAllByText('Close')[0];
    fireEvent.click(firstClose);
    expect(screen.getAllByTestId('notification')).toHaveLength(1);
  });
});
