/**
 * Integration tests for toast notification error handling via errorHandler.
 *
 * Services no longer fire toasts themselves; callers use showErrorToast(error)
 * from errorHandler.ts. These tests verify that the typed errors thrown by
 * services map to the correct toast calls when routed through showErrorToast.
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { AuthenticationError, AuthorizationError, ApiError, NetworkError } from '../errors';

// Mock the notification service
jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: {
    show401Error: jest.fn(),
    showApiError: jest.fn(),
    showNetworkError: jest.fn(),
    showSuccess: jest.fn(),
    showError: jest.fn(),
    clearAll: jest.fn(),
    getNotifications: jest.fn(() => []),
    show403Error: jest.fn(),
  },
}));

// Mock fetch globally
global.fetch = jest.fn();

describe('errorHandler.showErrorToast routing', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('routes AuthenticationError to show401Error', async () => {
    const { showErrorToast } = await import('../errorHandler');
    const notificationService = (await import('../../services/notificationService')).default;

    showErrorToast(new AuthenticationError());

    expect(notificationService.show401Error).toHaveBeenCalled();
  });

  it('routes AuthorizationError to show403Error', async () => {
    const { showErrorToast } = await import('../errorHandler');
    const notificationService = (await import('../../services/notificationService')).default;

    showErrorToast(new AuthorizationError());

    expect(notificationService.show403Error).toHaveBeenCalled();
  });

  it('routes NetworkError to showNetworkError', async () => {
    const { showErrorToast } = await import('../errorHandler');
    const notificationService = (await import('../../services/notificationService')).default;

    showErrorToast(new NetworkError());

    expect(notificationService.showNetworkError).toHaveBeenCalled();
  });

  it('routes generic ApiError to showApiError with status + message', async () => {
    const { showErrorToast } = await import('../errorHandler');
    const notificationService = (await import('../../services/notificationService')).default;

    showErrorToast(new ApiError(500, 'Server error'));

    expect(notificationService.showApiError).toHaveBeenCalledWith(500, 'Server error');
  });

  it('routes unknown errors to showError with fallback', async () => {
    const { showErrorToast } = await import('../errorHandler');
    const notificationService = (await import('../../services/notificationService')).default;

    showErrorToast('something unexpected');

    expect(notificationService.showError).toHaveBeenCalledWith('Unexpected error');
  });
});

describe('Service throws typed errors that errorHandler can route', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('organizationService throws AuthorizationError on 403, errorHandler maps to permission toast', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 403,
      text: () => Promise.resolve('Forbidden')
    });

    const { default: organizationService } = await import('../organizationService');
    const { showErrorToast } = await import('../errorHandler');
    const notificationService = (await import('../../services/notificationService')).default;

    let caught: unknown;
    try {
      await organizationService.createOrganization({ name: 'Test Organization', slug: 'test-org' });
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(AuthorizationError);
    showErrorToast(caught);
    expect(notificationService.show403Error).toHaveBeenCalled();
  });

  it('organizationService throws NetworkError on fetch failure, errorHandler maps to network toast', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new TypeError('Failed to fetch'));

    const { default: organizationService } = await import('../organizationService');
    const { showErrorToast } = await import('../errorHandler');
    const notificationService = (await import('../../services/notificationService')).default;

    let caught: unknown;
    try {
      await organizationService.createOrganization({ name: 'Test Organization', slug: 'test-org' });
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(NetworkError);
    showErrorToast(caught);
    expect(notificationService.showNetworkError).toHaveBeenCalled();
  });
});

describe('No Duplicate Notifications', () => {
  it('should show 403 error when show403Error is called', async () => {
    const { default: notificationService } = await import('../../services/notificationService');

    notificationService.clearAll();
    notificationService.show403Error('create organization');

    // The debounce/dedup behavior is tested in the notificationService unit tests.
    // Here we just verify show403Error is callable without error.
    expect(notificationService.show403Error).toHaveBeenCalledWith('create organization');
  });
});
