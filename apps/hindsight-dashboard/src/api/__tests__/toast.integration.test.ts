/**
 * Tests for toast notification error handling
 * 
 * This test suite verifies that toast notifications appear correctly
 * for different error scenarios to prevent silent failures.
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';

// Mock fetch globally for these tests
global.fetch = jest.fn();

describe('Toast Notification Error Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Permission Error Scenarios', () => {
    it('should show 403 permission error toast for organization creation', async () => {
      // Mock the actual notification service 
      const { default: notificationService } = await import('../../services/notificationService');
      const { default: organizationService } = await import('../organizationService');
      
      // Clear any existing notifications
      notificationService.clearAll();
      
      // Mock 403 response
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 403,
        text: () => Promise.resolve('Forbidden')
      });
      
      // Attempt to create organization
      try {
        await organizationService.createOrganization({
          name: 'Test Organization',
          slug: 'test-org'
        });
      } catch (error) {
        // Expected to fail
      }
      
      // Verify toast notification was created
      const notifications = notificationService.getNotifications();
      expect(notifications.length).toBeGreaterThan(0);
      
      const errorNotification = notifications.find(n => n.type === 'error');
      expect(errorNotification).toBeDefined();
      expect(errorNotification?.message).toContain('Permission denied (403)');
      expect(errorNotification?.message).toContain('create organization');
    });

    it('should show network error toast for fetch failures', async () => {
      const { default: notificationService } = await import('../../services/notificationService');
      const { default: organizationService } = await import('../organizationService');
      
      notificationService.clearAll();
      
      // Mock network failure
      (fetch as jest.Mock).mockRejectedValueOnce(new TypeError('Failed to fetch'));
      
      try {
        await organizationService.createOrganization({
          name: 'Test Organization',
          slug: 'test-org'
        });
      } catch (error) {
        // Expected to fail
      }
      
      const notifications = notificationService.getNotifications();
      expect(notifications.length).toBeGreaterThan(0);
      
      const errorNotification = notifications.find(n => 
        n.type === 'error' && n.message.includes('Network error')
      );
      expect(errorNotification).toBeDefined();
    });
  });

  describe('Success Scenarios', () => {
    it('should show success toast when organization is created successfully', async () => {
      const { default: notificationService } = await import('../../services/notificationService');
      const { default: organizationService } = await import('../organizationService');
      
      notificationService.clearAll();
      
      // Mock successful response
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: () => Promise.resolve({
          id: '123',
          name: 'Test Organization',
          slug: 'test-org',
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-01T00:00:00Z'
        })
      });
      
      await organizationService.createOrganization({
        name: 'Test Organization',
        slug: 'test-org'
      });
      
      const notifications = notificationService.getNotifications();
      expect(notifications.length).toBeGreaterThan(0);
      
      const successNotification = notifications.find(n => n.type === 'success');
      expect(successNotification).toBeDefined();
      expect(successNotification?.message).toContain('created successfully');
    });
  });

  describe('Error Code Mapping', () => {
    it('should handle different HTTP error codes appropriately', async () => {
      const { default: notificationService } = await import('../../services/notificationService');
      
      const testCases = [
        { status: 400, expectedText: 'Bad request (400)' },
        { status: 403, expectedText: 'Permission denied (403)' },
        { status: 404, expectedText: 'not found (404)' },
        { status: 429, expectedText: 'Too many requests (429)' },
        { status: 500, expectedText: 'Server error (500)' }
      ];
      
      for (const testCase of testCases) {
        notificationService.clearAll();
        
        const notificationId = notificationService.showApiError(
          testCase.status,
          undefined,
          'test action'
        );
        
        expect(notificationId).not.toBeNull();
        
        const notifications = notificationService.getNotifications();
        expect(notifications.length).toBe(1);
        expect(notifications[0].message).toContain(testCase.expectedText);
      }
    });
  });

  describe('No Duplicate Notifications', () => {
    it('should not show duplicate error notifications', async () => {
      const { default: notificationService } = await import('../../services/notificationService');
      
      notificationService.clearAll();
      
      // Try to add the same error notification twice
      const id1 = notificationService.show403Error('create organization');
      const id2 = notificationService.show403Error('create organization');
      
      expect(id1).not.toBeNull();
      expect(id2).toBeNull(); // Should be debounced
      
      const notifications = notificationService.getNotifications();
      expect(notifications.length).toBe(1);
    });
  });

  describe('UI Integration', () => {
    it('should verify notification appears in bottom-right position', async () => {
      // This test would ideally be done with a component test
      // For now, we test that notifications have the correct structure
      const { default: notificationService } = await import('../../services/notificationService');
      
      notificationService.clearAll();
      notificationService.show403Error('test action');
      
      const notifications = notificationService.getNotifications();
      expect(notifications[0]).toMatchObject({
        type: 'error',
        message: expect.stringContaining('Permission denied'),
        duration: 10000
      });
    });
  });
});
