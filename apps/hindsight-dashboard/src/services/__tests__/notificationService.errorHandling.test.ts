/**
 * Tests for enhanced notification service error handling
 * 
 * This test suite verifies that the notification service properly shows
 * toast notifications for different types of API errors.
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import notificationService from '../notificationService';

describe('NotificationService Enhanced Error Handling', () => {
  beforeEach(() => {
    // Clear all notifications before each test
    notificationService.clearAll();
    
    // Mock Date.now for consistent testing
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2023-01-01'));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('HTTP Status Code Error Messages', () => {
    it('should show 403 permission error toast', () => {
      const id = notificationService.show403Error('create organization');
      
      expect(id).not.toBeNull();
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].type).toBe('error');
      expect(notifications[0].message).toContain('Permission denied (403)');
      expect(notifications[0].message).toContain('create organization');
      expect(notifications[0].duration).toBe(10000);
    });

    it('should show 404 resource not found error toast', () => {
      const id = notificationService.show404Error('organization');
      
      expect(id).not.toBeNull();
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].type).toBe('error');
      expect(notifications[0].message).toContain('organization not found (404)');
      expect(notifications[0].duration).toBe(8000);
    });

    it('should show 500 server error toast', () => {
      const id = notificationService.show500Error();
      
      expect(id).not.toBeNull();
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].type).toBe('error');
      expect(notifications[0].message).toContain('Server error (500)');
      expect(notifications[0].duration).toBe(10000);
    });

    it('should show network error toast', () => {
      const id = notificationService.showNetworkError();
      
      expect(id).not.toBeNull();
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].type).toBe('error');
      expect(notifications[0].message).toContain('Network error');
      expect(notifications[0].duration).toBe(8000);
    });
  });

  describe('Generic API Error Handler', () => {
    it('should handle 400 bad request errors', () => {
      const id = notificationService.showApiError(400, 'Invalid input data', 'submit form');
      
      expect(id).not.toBeNull();
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].message).toContain('Bad request (400)');
      expect(notifications[0].message).toContain('Invalid input data');
    });

    it('should delegate 401 errors to show401Error', () => {
      const id = notificationService.showApiError(401, undefined, 'access resource');
      
      expect(id).not.toBeNull();
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].message).toContain('Authentication error (401)');
      expect(notifications[0].onRefresh).toBeDefined();
    });

    it('should delegate 403 errors to show403Error', () => {
      const id = notificationService.showApiError(403, undefined, 'delete resource');
      
      expect(id).not.toBeNull();
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].message).toContain('Permission denied (403)');
      expect(notifications[0].message).toContain('delete resource');
    });

    it('should handle 429 rate limiting errors', () => {
      const id = notificationService.showApiError(429, undefined, 'make request');
      
      expect(id).not.toBeNull();
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].message).toContain('Too many requests (429)');
    });

    it('should delegate 500/502/503/504 errors to show500Error', () => {
      [500, 502, 503, 504].forEach(status => {
        notificationService.clearAll();
        const id = notificationService.showApiError(status, undefined, 'process request');
        
        expect(id).not.toBeNull();
        const notifications = notificationService.getNotifications();
        expect(notifications).toHaveLength(1);
        expect(notifications[0].message).toContain('Server error (500)');
      });
    });

    it('should handle unknown status codes with custom message', () => {
      const id = notificationService.showApiError(418, 'I am a teapot', 'brew coffee');
      
      expect(id).not.toBeNull();
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].message).toBe('Error (418): I am a teapot');
    });

    it('should handle unknown status codes without custom message', () => {
      const id = notificationService.showApiError(999, undefined, 'perform action');
      
      expect(id).not.toBeNull();
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].message).toContain('Unexpected error (999)');
      expect(notifications[0].message).toContain('perform action');
    });
  });

  describe('Error Debouncing', () => {
    it('should debounce identical 403 errors', () => {
      const id1 = notificationService.show403Error('create organization');
      const id2 = notificationService.show403Error('create organization');
      
      expect(id1).not.toBeNull();
      expect(id2).toBeNull(); // Should be debounced
      
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
    });

    it('should not debounce different error types', () => {
      const id1 = notificationService.show403Error('create organization');
      const id2 = notificationService.show404Error('organization');
      
      expect(id1).not.toBeNull();
      expect(id2).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(2);
    });

    it('should allow same error after debounce period', () => {
      const id1 = notificationService.show403Error('create organization');
      expect(id1).not.toBeNull();
      
      // Advance time past debounce period
      jest.advanceTimersByTime(6000);
      
      const id2 = notificationService.show403Error('create organization');
      expect(id2).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(2);
    });
  });

  describe('Integration with existing functionality', () => {
    it('should maintain existing 401 error behavior with refresh button', () => {
      // Mock window.location for redirect test
      const originalLocation = window.location;
      
      Object.defineProperty(window, 'location', {
        value: {
          href: '',
          pathname: '/test',
          search: '?q=1',
          hash: '#section'
        },
        writable: true
      });
      
      const id = notificationService.show401Error();
      
      expect(id).not.toBeNull();
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].onRefresh).toBeDefined();
      expect(notifications[0].duration).toBe(30000);
      
      // Test refresh callback
      notifications[0].onRefresh!();
      expect(window.location.href).toContain('/oauth2/sign_in');
      expect(window.location.href).toContain('rd=');
      
      // Restore window.location
      Object.defineProperty(window, 'location', {
        value: originalLocation,
        writable: true
      });
    });

    it('should work alongside existing success/info/warning methods', () => {
      notificationService.showSuccess('Success message');
      notificationService.showInfo('Info message');
      notificationService.showWarning('Warning message');
      notificationService.show403Error('test action');
      
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(4);
      
      const types = notifications.map(n => n.type);
      expect(types).toEqual(['success', 'info', 'warning', 'error']);
    });
  });
});
