/**
 * Tests for API service typed error handling
 *
 * The API services no longer fire toast notifications directly; they throw
 * typed errors (AuthenticationError, AuthorizationError, ApiError, NetworkError)
 * so callers can decide how to surface them to the user.
 */

import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';
import organizationService from '../organizationService';
import { AuthenticationError, AuthorizationError, ApiError, NetworkError } from '../errors';

describe('OrganizationService Typed Error Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('createOrganization', () => {
    it('should throw AuthorizationError (403) so callers can show permission toast', async () => {
      const mockResponse = {
        ok: false,
        status: 403,
        text: jest.fn().mockResolvedValue('<html><body><h1>403 Forbidden</h1></body></html>')
      };

      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

      await expect(organizationService.createOrganization({
        name: 'Test Org',
        slug: 'test-org'
      })).rejects.toThrow(AuthorizationError);
    });

    it('should throw ApiError(400) with message for bad request', async () => {
      const mockResponse = {
        ok: false,
        status: 400,
        text: jest.fn().mockResolvedValue('Organization name already exists')
      };

      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

      const err = await organizationService.createOrganization({
        name: 'Duplicate Org',
        slug: 'duplicate-org'
      }).catch(e => e);

      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(400);
    });

    it('should throw NetworkError for fetch failures', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new TypeError('Failed to fetch'));

      await expect(organizationService.createOrganization({
        name: 'Test Org',
        slug: 'test-org'
      })).rejects.toThrow(NetworkError);
    });

    it('should return organization data on success without firing any toast', async () => {
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
    });

    it('should throw ApiError(500) for server errors', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        text: jest.fn().mockResolvedValue('Internal Server Error')
      };

      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

      const err = await organizationService.createOrganization({
        name: 'Test Org',
        slug: 'test-org'
      }).catch(e => e);

      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(500);
    });
  });

  describe('getOrganizations', () => {
    it('should throw ApiError for non-401 errors', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        text: jest.fn().mockResolvedValue('Server Error')
      };

      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

      const err = await organizationService.getOrganizations().catch(e => e);
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(500);
    });

    it('should throw AuthenticationError for 401 errors', async () => {
      const mockResponse = {
        ok: false,
        status: 401,
        text: jest.fn().mockResolvedValue('Unauthorized')
      };

      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

      await expect(organizationService.getOrganizations()).rejects.toThrow(AuthenticationError);
    });

    it('should throw NetworkError for fetch failures', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new TypeError('Failed to fetch'));

      await expect(organizationService.getOrganizations()).rejects.toThrow(NetworkError);
    });

    it('should return organizations on success', async () => {
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
    });
  });
});
