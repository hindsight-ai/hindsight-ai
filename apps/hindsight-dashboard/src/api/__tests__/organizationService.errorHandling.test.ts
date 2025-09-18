/**
 * Tests for API service error handling and toast notifications
 * 
 * This test suite verifies that API services properly show toast notifications
 * for different error scenarios, especially the 403 permission errors.
 */

import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';
import organizationService from '../organizationService';
import notificationService from '../../services/notificationService';

// Mock the notification service
jest.mock('../../services/notificationService', () => ({
  showApiError: jest.fn(),
  showNetworkError: jest.fn(),
  showSuccess: jest.fn(),
  showError: jest.fn(),
  clearAll: jest.fn(),
  getNotifications: jest.fn(() => []),
}));

const mockNotificationService = notificationService as jest.Mocked<typeof notificationService>;

describe('OrganizationService Error Handling', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    
    // Reset fetch mock
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('createOrganization', () => {
    it('should show 403 permission error toast when user lacks permission', async () => {
      const mockResponse = {
        ok: false,
        status: 403,
        text: jest.fn().mockResolvedValue('<html><body><h1>403 Forbidden</h1></body></html>')
      };
      
      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);
      
      await expect(organizationService.createOrganization({
        name: 'Test Org',
        slug: 'test-org'
      })).rejects.toThrow('HTTP error 403');
      
      expect(mockNotificationService.showApiError).toHaveBeenCalledWith(
        403,
        '<html><body><h1>403 Forbidden</h1></body></html>',
        'create organization'
      );
    });

    it('should show 400 bad request error toast with message', async () => {
      const errorMessage = 'Organization name already exists';
      const mockResponse = {
        ok: false,
        status: 400,
        text: jest.fn().mockResolvedValue(errorMessage)
      };
      
      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);
      
      await expect(organizationService.createOrganization({
        name: 'Duplicate Org',
        slug: 'duplicate-org'
      })).rejects.toThrow('HTTP error 400');
      
      expect(mockNotificationService.showApiError).toHaveBeenCalledWith(
        400,
        errorMessage,
        'create organization'
      );
    });

    it('should show network error toast for fetch failures', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new TypeError('Failed to fetch'));
      
      await expect(organizationService.createOrganization({
        name: 'Test Org',
        slug: 'test-org'
      })).rejects.toThrow('Failed to fetch');
      
      expect(mockNotificationService.showNetworkError).toHaveBeenCalled();
    });

    it('should show success toast when organization is created successfully', async () => {
      const mockOrganization = {
        id: '123',
        name: 'Test Org',
        slug: 'test-org',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z'
      };
      
      const mockResponse = {
        ok: true,
        status: 201,
        json: jest.fn().mockResolvedValue(mockOrganization)
      };
      
      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);
      
      const result = await organizationService.createOrganization({
        name: 'Test Org',
        slug: 'test-org'
      });
      
      expect(result).toEqual(mockOrganization);
      expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
        'Organization created successfully!'
      );
    });

    it('should not show duplicate notifications for generic errors when specific error already shown', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        text: jest.fn().mockResolvedValue('Internal Server Error')
      };
      
      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);
      
      await expect(organizationService.createOrganization({
        name: 'Test Org',
        slug: 'test-org'
      })).rejects.toThrow('HTTP error 500');
      
      // Should call showApiError but not showError (to avoid duplicates)
      expect(mockNotificationService.showApiError).toHaveBeenCalledWith(
        500,
        'Internal Server Error',
        'create organization'
      );
      expect(mockNotificationService.showError).not.toHaveBeenCalled();
    });
  });

  describe('getOrganizations', () => {
    it('should show API error toast for non-401 errors', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        text: jest.fn().mockResolvedValue('Server Error')
      };
      
      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);
      
      await expect(organizationService.getOrganizations()).rejects.toThrow('HTTP error 500');
      
      expect(mockNotificationService.showApiError).toHaveBeenCalledWith(
        500,
        undefined,
        'fetch organizations'
      );
    });

    it('should not show API error toast for 401 errors (handled by auth interceptor)', async () => {
      const mockResponse = {
        ok: false,
        status: 401,
        text: jest.fn().mockResolvedValue('Unauthorized')
      };
      
      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);
      
      await expect(organizationService.getOrganizations()).rejects.toThrow('HTTP error 401');
      
      // Should not call showApiError for 401 errors
      expect(mockNotificationService.showApiError).not.toHaveBeenCalled();
    });

    it('should show network error toast for fetch failures', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new TypeError('Failed to fetch'));
      
      await expect(organizationService.getOrganizations()).rejects.toThrow('Failed to fetch');
      
      expect(mockNotificationService.showNetworkError).toHaveBeenCalled();
    });

    it('should succeed without showing any error notifications', async () => {
      const mockOrganizations = [
        { id: '1', name: 'Org 1', slug: 'org-1', created_at: '2023-01-01T00:00:00Z', updated_at: '2023-01-01T00:00:00Z' },
        { id: '2', name: 'Org 2', slug: 'org-2', created_at: '2023-01-01T00:00:00Z', updated_at: '2023-01-01T00:00:00Z' }
      ];
      
      const mockResponse = {
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue(mockOrganizations)
      };
      
      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);
      
      const result = await organizationService.getOrganizations();
      
      expect(result).toEqual(mockOrganizations);
      expect(mockNotificationService.showApiError).not.toHaveBeenCalled();
      expect(mockNotificationService.showNetworkError).not.toHaveBeenCalled();
      expect(mockNotificationService.showError).not.toHaveBeenCalled();
    });
  });
});

describe('Error Toast Integration Test', () => {
  it('should show actual toast notification for 403 error', async () => {
    const mockResponse = {
      ok: false,
      status: 403,
      text: jest.fn().mockResolvedValue('Forbidden')
    };

    (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

    await expect(organizationService.createOrganization({
      name: 'Test Org',
      slug: 'test-org'
    })).rejects.toThrow('HTTP error 403');

    // Verify that showApiError was called with correct parameters
    expect(mockNotificationService.showApiError).toHaveBeenCalledWith(403, 'Forbidden', 'create organization');
  });
});
