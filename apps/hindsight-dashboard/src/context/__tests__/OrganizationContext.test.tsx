import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { OrganizationProvider, useOrganization } from '../OrganizationContext';
import { useAuth } from '../AuthContext';
import organizationService from '../../api/organizationService';

// Mock the organization service
jest.mock('../../api/organizationService');
const mockOrganizationService = organizationService as jest.Mocked<typeof organizationService>;

// Mock the useAuth hook
jest.mock('../AuthContext', () => ({
  useAuth: jest.fn(),
}));
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <OrganizationProvider>{children}</OrganizationProvider>
);

describe('OrganizationContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
    mockUseAuth.mockReturnValue({
      user: { authenticated: true, email: 'test@example.com' } as any,
      loading: false,
      guest: false,
      enterGuestMode: jest.fn(),
      exitGuestMode: jest.fn(),
      refresh: jest.fn(),
    });
  });

  test('starts in personal mode by default', () => {
    const { result } = renderHook(() => useOrganization(), { wrapper });

    expect(result.current.isPersonalMode).toBe(true);
    expect(result.current.currentOrganization).toBeNull();
    expect(result.current.currentUserMembership).toBeNull();
  });

  test('loads user organizations on mount', async () => {
    const mockOrganizations = [
      { id: 'org1', name: 'Test Org 1', is_active: true },
      { id: 'org2', name: 'Test Org 2', is_active: true },
    ];

    mockOrganizationService.getOrganizations.mockResolvedValue(mockOrganizations);

    const { result } = renderHook(() => useOrganization(), { wrapper });

    // Wait for the async operation to complete
    await act(async () => {
      // The effect runs automatically on mount
      await new Promise(resolve => setTimeout(resolve, 0));
    });

    expect(mockOrganizationService.getOrganizations).toHaveBeenCalled();
    expect(result.current.userOrganizations).toEqual(mockOrganizations);
  });

  test('switches to organization mode', async () => {
    const mockOrganizations = [
      { id: 'org1', name: 'Test Org 1', is_active: true },
    ];
    const mockMembers = [
      {
        user_id: 'user1',
        email: 'test@example.com',
        display_name: 'Test User',
        role: 'admin',
        can_read: true,
        can_write: true,
      },
    ];

    mockOrganizationService.getOrganizations.mockResolvedValue(mockOrganizations);
    mockOrganizationService.getOrganization.mockResolvedValue(mockOrganizations[0]);
    mockOrganizationService.getMembers.mockResolvedValue(mockMembers);

    const { result } = renderHook(() => useOrganization(), { wrapper });

    await act(async () => {
      await result.current.switchToOrganization('org1');
    });

    expect(result.current.isPersonalMode).toBe(false);
    expect(result.current.currentOrganization).toEqual(mockOrganizations[0]);
    expect(result.current.currentUserMembership).toEqual(mockMembers[0]);
    expect(localStorageMock.setItem).toHaveBeenCalledWith('selectedOrganizationId', 'org1');
  });

  test('switches back to personal mode', async () => {
    const { result } = renderHook(() => useOrganization(), { wrapper });

    act(() => {
      result.current.switchToPersonal();
    });

    expect(result.current.isPersonalMode).toBe(true);
    expect(result.current.currentOrganization).toBeNull();
    expect(result.current.currentUserMembership).toBeNull();
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('selectedOrganizationId');
  });

  test('handles organization switching errors gracefully', async () => {
    const mockError = new Error('Organization not found');
    mockOrganizationService.getOrganization.mockRejectedValue(mockError);

    const { result } = renderHook(() => useOrganization(), { wrapper });

    await act(async () => {
      await result.current.switchToOrganization('invalid-org');
    });

    expect(result.current.isPersonalMode).toBe(true);
    expect(result.current.error).toContain('Failed to switch to organization');
  });

  test('restores saved organization on mount', async () => {
    const mockOrganizations = [
      { id: 'org1', name: 'Test Org 1', is_active: true },
    ];
    const mockMembers = [
      {
        user_id: 'user1',
        email: 'test@example.com',
        display_name: 'Test User',
        role: 'admin',
        can_read: true,
        can_write: true,
      },
    ];

    localStorageMock.getItem.mockReturnValue('org1');
    mockOrganizationService.getOrganizations.mockResolvedValue(mockOrganizations);
    mockOrganizationService.getOrganization.mockResolvedValue(mockOrganizations[0]);
    mockOrganizationService.getMembers.mockResolvedValue(mockMembers);

    const { result } = renderHook(() => useOrganization(), { wrapper });

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });

    expect(result.current.isPersonalMode).toBe(false);
    expect(result.current.currentOrganization).toEqual(mockOrganizations[0]);
  });
});
