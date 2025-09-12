/**
 * Tests for toast notification error handling
 * 
 * This test suite verifies that toast notifications appear correctly
 * for different error scenarios to prevent silent failures.
 */

import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';
import notificationService from '../notificationService';

describe('Toast Notification Error Handling', () => {
  let testStartTime = 0;
  
  beforeEach(() => {
    // Clear all notifications before each test
    notificationService.clearAll();
    
    // Use fake timers to control debouncing
    jest.useFakeTimers();
    
    // Set a unique start time for each test to avoid debouncing conflicts
    testStartTime += 60000; // 1 minute between each test
    jest.setSystemTime(new Date(testStartTime));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('403 Forbidden Errors', () => {
    it('should show 403 error toast for permission denied', () => {
      const notificationId = notificationService.show403Error('organization creation');
      
      expect(notificationId).not.toBeNull();
      expect(typeof notificationId).toBe('number');
      
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].type).toBe('error');
      expect(notifications[0].message).toBe('Permission denied (403). You don\'t have permission to organization creation. Please contact your administrator if you believe this is incorrect.');
    });

    it('should show generic 403 error when no action specified', () => {
      const notificationId = notificationService.show403Error();
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications[0].message).toBe('Permission denied (403). You don\'t have permission to perform this action. Please contact your administrator if you believe this is incorrect.');
    });

    it('should handle multiple 403 errors with debouncing', () => {
      const firstId = notificationService.show403Error('create organization');
      
      // Advance time by 1 second (still within debounce window)
      jest.advanceTimersByTime(1000);
      const secondId = notificationService.show403Error('create organization');
      
      // Should be debounced (same action)
      expect(firstId).not.toBeNull();
      expect(secondId).toBeNull();
      expect(notificationService.getNotifications()).toHaveLength(1);
      
      // Advance time beyond debounce window
      jest.advanceTimersByTime(5000);
      const thirdId = notificationService.show403Error('create organization');
      
      // Should create new notification after debounce expires
      expect(thirdId).not.toBeNull();
      expect(notificationService.getNotifications()).toHaveLength(2);
    });
  });

  describe('Network Errors', () => {
    it('should show network error toast for connection issues', () => {
      const notificationId = notificationService.showNetworkError();
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].type).toBe('error');
      expect(notifications[0].message).toBe('Network error. Please check your internet connection and try again.');
    });
  });

  describe('HTTP Status Code Errors', () => {
    it('should show 404 error toast for not found', () => {
      const notificationId = notificationService.show404Error('Organization');
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications[0].type).toBe('error');
      expect(notifications[0].message).toBe('Organization not found (404). The Organization may have been moved or deleted.');
    });

    it('should show generic 404 error when no resource specified', () => {
      const notificationId = notificationService.show404Error();
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications[0].message).toBe('resource not found (404). The resource may have been moved or deleted.');
    });

    it('should show 500 error toast for server errors', () => {
      const notificationId = notificationService.show500Error();
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications[0].type).toBe('error');
      expect(notifications[0].message).toBe('Server error (500). Something went wrong on our end. Please try again later.');
    });

    it('should show 401 error toast for authentication errors', () => {
      const notificationId = notificationService.show401Error();
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications[0].type).toBe('error');
      expect(notifications[0].message).toBe('Authentication error (401). Your session may have expired. Please refresh authentication to continue.');
      expect(notifications[0].duration).toBe(30000);
      expect(notifications[0].onRefresh).toBeDefined();
    });
  });

  describe('Generic API Errors', () => {
    it('should show API error toast with status code 400', () => {
      const notificationId = notificationService.showApiError(400, 'Invalid input data');
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications[0].type).toBe('error');
      expect(notifications[0].message).toBe('Bad request (400). Invalid input data');
    });

    it('should show API error toast with status code 429', () => {
      const notificationId = notificationService.showApiError(429);
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications[0].message).toBe('Too many requests (429). Please wait a moment before trying again.');
    });

    it('should delegate to specific error handlers for known status codes', () => {
      // Test 403 delegation
      const notificationId403 = notificationService.showApiError(403, undefined, 'create organization');
      expect(notificationId403).not.toBeNull();
      
      let notifications = notificationService.getNotifications();
      expect(notifications[notifications.length - 1].message).toContain('Permission denied (403)');
      
      notificationService.clearAll();
      
      // Test 500 delegation
      const notificationId500 = notificationService.showApiError(500);
      expect(notificationId500).not.toBeNull();
      
      notifications = notificationService.getNotifications();
      expect(notifications[notifications.length - 1].message).toContain('Server error (500)');
    });

    it('should handle unknown status codes with fallback message', () => {
      const notificationId = notificationService.showApiError(418, 'I am a teapot', 'brew coffee');
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications[notifications.length - 1].message).toBe('Error (418): I am a teapot');
    });

    it('should provide fallback message for unknown status codes without custom message', () => {
      const notificationId = notificationService.showApiError(422, undefined, 'process data');
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications[notifications.length - 1].message).toBe('Unexpected error (422) occurred while trying to process data.');
    });
  });

  describe('Error Notification Properties', () => {
    it('should set correct duration for different error types', () => {
      const id403 = notificationService.show403Error();
      notificationService.clearAll();
      
      const id404 = notificationService.show404Error();
      notificationService.clearAll();
      
      const id500 = notificationService.show500Error();
      
      const notifications = notificationService.getNotifications();
      expect(notifications[0].duration).toBe(10000); // 500 error duration
    });

    it('should set error type for all error notifications', () => {
      notificationService.show403Error();
      notificationService.clearAll();
      
      notificationService.show404Error();
      notificationService.clearAll();
      
      notificationService.show500Error();
      notificationService.clearAll();
      
      notificationService.showNetworkError();
      
      const notifications = notificationService.getNotifications();
      notifications.forEach(notification => {
        expect(notification.type).toBe('error');
      });
    });

    it('should generate unique IDs for error notifications', () => {
      const ids = new Set();
      
      // Generate multiple notifications with clearAll between them
      for (let i = 0; i < 5; i++) {
        const id = notificationService.show403Error(`action ${i}`);
        if (id) ids.add(id);
        notificationService.clearAll();
      }
      
      expect(ids.size).toBe(5); // All IDs should be unique
    });
  });

  describe('Notification Management', () => {
    it('should clear all notifications', () => {
      notificationService.show403Error();
      notificationService.clearAll();
      notificationService.show404Error();
      
      expect(notificationService.getNotifications()).toHaveLength(1);
      
      notificationService.clearAll();
      expect(notificationService.getNotifications()).toHaveLength(0);
    });

    it('should remove specific notifications', () => {
      const id1 = notificationService.show403Error('action 1');
      notificationService.clearAll();
      
      const id2 = notificationService.show404Error('resource 2');
      
      expect(notificationService.getNotifications()).toHaveLength(1);
      
      if (id2) {
        notificationService.removeNotification(id2);
        expect(notificationService.getNotifications()).toHaveLength(0);
      }
    });
  });
});

describe('Toast Notification Error Handling', () => {
  beforeEach(() => {
    // Clear all notifications before each test
    notificationService.clearAll();
  });

  describe('Permission Error Scenarios', () => {
    it('should show 403 permission error toast with appropriate message', () => {
      const notificationId = notificationService.show403Error('create organization');
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      
      const errorNotification = notifications[0];
      expect(errorNotification.type).toBe('error');
      expect(errorNotification.message).toContain('Permission denied (403)');
      expect(errorNotification.message).toContain('create organization');
      expect(errorNotification.duration).toBe(10000);
    });

    it('should show generic permission error when no specific action provided', () => {
      const notificationId = notificationService.show403Error();
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      
      const errorNotification = notifications[0];
      expect(errorNotification.message).toContain('Permission denied (403)');
      expect(errorNotification.message).toContain('perform this action');
    });
  });

  describe('Network Error Scenarios', () => {
    it('should show network error toast with connectivity message', () => {
      const notificationId = notificationService.showNetworkError();
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      
      const errorNotification = notifications[0];
      expect(errorNotification.type).toBe('error');
      expect(errorNotification.message).toContain('Network error');
      expect(errorNotification.message).toContain('internet connection');
      expect(errorNotification.duration).toBe(8000);
    });
  });

  describe('API Error Code Mapping', () => {
    it('should handle 400 bad request errors', () => {
      const notificationId = notificationService.showApiError(
        400, 
        'Invalid organization name', 
        'create organization'
      );
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      const errorNotification = notifications[0];
      expect(errorNotification.message).toContain('Bad request (400)');
      expect(errorNotification.message).toContain('Invalid organization name');
    });

    it('should delegate 401 errors to show401Error', () => {
      const notificationId = notificationService.showApiError(401, undefined, 'access resource');
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      const errorNotification = notifications[0];
      expect(errorNotification.message).toContain('Authentication error (401)');
      expect(errorNotification.onRefresh).toBeDefined();
      expect(errorNotification.duration).toBe(30000);
    });

    it('should delegate 403 errors to show403Error', () => {
      const notificationId = notificationService.showApiError(403, undefined, 'delete resource');
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      const errorNotification = notifications[0];
      expect(errorNotification.message).toContain('Permission denied (403)');
      expect(errorNotification.message).toContain('delete resource');
    });

    it('should handle 404 not found errors', () => {
      const notificationId = notificationService.showApiError(404, undefined, 'find organization');
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      const errorNotification = notifications[0];
      expect(errorNotification.message).toContain('not found (404)');
    });

    it('should handle 429 rate limiting errors', () => {
      const notificationId = notificationService.showApiError(429, undefined, 'make request');
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      const errorNotification = notifications[0];
      expect(errorNotification.message).toContain('Too many requests (429)');
    });

    it('should handle 500+ server errors', () => {
      const serverErrorCodes = [500, 502, 503, 504];
      
      serverErrorCodes.forEach((statusCode, index) => {
        notificationService.clearAll();
        
        const notificationId = notificationService.showApiError(statusCode, undefined, 'process request');
        
        expect(notificationId).not.toBeNull();
        
        const notifications = notificationService.getNotifications();
        const errorNotification = notifications[0];
        expect(errorNotification.message).toContain('Server error (500)');
      });
    });

    it('should handle unknown error codes with generic message', () => {
      const notificationId = notificationService.showApiError(999, undefined, 'perform action');
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      const errorNotification = notifications[0];
      expect(errorNotification.message).toContain('Unexpected error (999)');
      expect(errorNotification.message).toContain('perform action');
    });
  });

  describe('Error Debouncing Prevention', () => {
    it('should prevent duplicate 403 error notifications', () => {
      const id1 = notificationService.show403Error('create organization');
      const id2 = notificationService.show403Error('create organization');
      
      expect(id1).not.toBeNull();
      expect(id2).toBeNull(); // Should be debounced
      
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
    });

    it('should allow different error types simultaneously', () => {
      const id1 = notificationService.show403Error('create organization');
      const id2 = notificationService.showNetworkError();
      const id3 = notificationService.show404Error('organization');
      
      expect(id1).not.toBeNull();
      expect(id2).not.toBeNull();
      expect(id3).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(3);
      
      const types = notifications.map(n => n.type);
      expect(types).toEqual(['error', 'error', 'error']);
    });
  });

  describe('Notification Structure Validation', () => {
    it('should create notifications with correct structure for bottom-right toast display', () => {
      const notificationId = notificationService.show403Error('test action');
      
      expect(notificationId).not.toBeNull();
      
      const notifications = notificationService.getNotifications();
      const notification = notifications[0];
      
      // Verify required properties for toast display
      expect(notification).toHaveProperty('id');
      expect(notification).toHaveProperty('type');
      expect(notification).toHaveProperty('message');
      expect(notification).toHaveProperty('duration');
      
      expect(typeof notification.id).toBe('number');
      expect(notification.type).toBe('error');
      expect(typeof notification.message).toBe('string');
      expect(typeof notification.duration).toBe('number');
      expect(notification.duration).toBeGreaterThan(0);
    });

    it('should create notifications with appropriate durations for different error types', () => {
      notificationService.show403Error('test');
      notificationService.showNetworkError();
      notificationService.show401Error();
      
      const notifications = notificationService.getNotifications();
      
      // 403 error: 10 seconds
      expect(notifications[0].duration).toBe(10000);
      
      // Network error: 8 seconds  
      expect(notifications[1].duration).toBe(8000);
      
      // 401 error: 30 seconds (longer for auth issues)
      expect(notifications[2].duration).toBe(30000);
    });
  });

  describe('Regression Test for Silent Failures', () => {
    it('should ensure error notifications are actually created and not silently ignored', () => {
      // Before our enhancement, errors were only logged to console
      // This test ensures they now create actual toast notifications
      
      const initialCount = notificationService.getNotifications().length;
      expect(initialCount).toBe(0);
      
      // Simulate the exact error scenario from the user's console logs
      notificationService.showApiError(403, 'Forbidden', 'create organization');
      
      const finalCount = notificationService.getNotifications().length;
      expect(finalCount).toBe(1);
      
      const notification = notificationService.getNotifications()[0];
      expect(notification.type).toBe('error');
      expect(notification.message).not.toBe('');
      
      // Verify this would be visible to the user (not just in console)
      expect(notification.duration).toBeGreaterThan(5000); // Visible for at least 5 seconds
    });

    it('should handle the exact Mixed Content + 403 error scenario from staging', () => {
      // Simulate the user's exact error scenario:
      // 1. Mixed Content errors (now fixed by protocol handling)
      // 2. 403 error when creating organization (now shows toast)
      
      notificationService.showApiError(403, 
        '<html><head><title>403 Forbidden</title></head><body><center><h1>403 Forbidden</h1></center></body></html>',
        'create organization'
      );
      
      const notifications = notificationService.getNotifications();
      expect(notifications).toHaveLength(1);
      
      const errorNotification = notifications[0];
      expect(errorNotification.type).toBe('error');
      expect(errorNotification.message).toContain('Permission denied (403)');
      expect(errorNotification.message).toContain('create organization');
      
      // Ensure this is a user-visible toast, not just a console log
      expect(errorNotification.duration).toBe(10000);
    });
  });
});
