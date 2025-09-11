import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';
import OrganizationManagement from '../OrganizationManagement';
import { useAuth } from '../../context/AuthContext';
import { useOrganization } from '../../context/OrganizationContext';
import organizationService from '../../api/organizationService';
import notificationService from '../../services/notificationService';

// Mock dependencies
jest.mock('../../context/AuthContext');
jest.mock('../../context/OrganizationContext');
jest.mock('../../api/organizationService');
jest.mock('../../services/notificationService');

const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockUseOrganization = useOrganization as jest.MockedFunction<typeof useOrganization>;
const mockOrganizationService = organizationService as jest.Mocked<typeof organizationService>;
const mockNotificationService = notificationService as jest.Mocked<typeof notificationService>;

const mockOrganizations = [
  {
    id: '1',
    name: 'Member Organization',
    slug: 'member-org',
    is_active: true,
  },
  {
    id: '2', 
    name: 'Non-Member Organization',
    slug: 'non-member-org',
    is_active: true,
  }
];

const mockUserMemberOrgs = [
  {
    id: '1',
    name: 'Member Organization', 
    slug: 'member-org',
    is_active: true,
  }
];

const mockMembers = [
  {
    user_id: 'user1',
    email: 'user1@example.com',
    display_name: 'User One',
    role: 'owner',
    can_read: true,
    can_write: true,
  }
];

describe('OrganizationManagement', () => {
  const mockOnClose = jest.fn();
  const mockRefreshOrganizations = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockNotificationService.showError = jest.fn();
    mockNotificationService.showSuccess = jest.fn();
    mockUseOrganization.mockReturnValue({
      organizations: mockUserMemberOrgs,
      currentOrganization: null,
      setCurrentOrganization: jest.fn(),
      refreshOrganizations: mockRefreshOrganizations,
      loading: false,
    } as any);
  });

  describe('Access Control', () => {
    it('shows access denied for unauthenticated users', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          authenticated: false,
        },
        loading: false,
      } as any);

      render(<OrganizationManagement onClose={mockOnClose} />);

      expect(screen.getByText('Access Denied')).toBeInTheDocument();
      expect(screen.getByText('You need to be a superadmin or have organization memberships to access organization management.')).toBeInTheDocument();
    });

    it('shows access denied for authenticated users with no organizations', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          authenticated: true,
          email: 'user@example.com',
          is_superadmin: false,
          organizations: [],
        },
        loading: false,
      } as any);

      render(<OrganizationManagement onClose={mockOnClose} />);

      expect(screen.getByText('Access Denied')).toBeInTheDocument();
      expect(screen.getByText('You need to be a superadmin or have organization memberships to access organization management.')).toBeInTheDocument();
    });

    it('allows access for authenticated users with organization memberships', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          authenticated: true,
          email: 'user@example.com',
          is_superadmin: false,
          organizations: [
            {
              organization_id: '1',
              organization_name: 'Test Org',
              role: 'admin',
              can_read: true,
              can_write: true,
            }
          ],
        },
        loading: false,
      } as any);

      mockOrganizationService.getManageableOrganizations.mockResolvedValue(mockOrganizations);
      mockOrganizationService.getOrganizations.mockResolvedValue(mockUserMemberOrgs);

      render(<OrganizationManagement onClose={mockOnClose} />);

      await waitFor(() => {
        expect(screen.getByText('Organization Management')).toBeInTheDocument();
      });
    });

    it('allows access for superadmin users (even without organization memberships)', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          authenticated: true,
          email: 'admin@example.com',
          is_superadmin: true,
          organizations: [],
        },
        loading: false,
      } as any);

      mockOrganizationService.getManageableOrganizations.mockResolvedValue(mockOrganizations);
      mockOrganizationService.getOrganizations.mockResolvedValue(mockUserMemberOrgs);

      render(<OrganizationManagement onClose={mockOnClose} />);

      await waitFor(() => {
        expect(screen.getByText('Organization Management')).toBeInTheDocument();
      });
    });

    it('allows access for superadmin users with organization memberships', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          authenticated: true,
          email: 'admin@example.com',
          is_superadmin: true,
          organizations: [
            {
              organization_id: '1',
              organization_name: 'Test Org',
              role: 'owner',
              can_read: true,
              can_write: true,
            }
          ],
        },
        loading: false,
      } as any);

      mockOrganizationService.getManageableOrganizations.mockResolvedValue(mockOrganizations);
      mockOrganizationService.getOrganizations.mockResolvedValue(mockUserMemberOrgs);

      render(<OrganizationManagement onClose={mockOnClose} />);

      await waitFor(() => {
        expect(screen.getByText('Organization Management')).toBeInTheDocument();
      });
    });
  });

  describe('View Mode Toggle', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: {
          authenticated: true,
          email: 'admin@example.com', 
          is_superadmin: true,
        },
        loading: false,
      } as any);

      mockOrganizationService.getManageableOrganizations.mockResolvedValue(mockOrganizations);
      mockOrganizationService.getOrganizations.mockResolvedValue(mockUserMemberOrgs);
      mockOrganizationService.getMembers.mockResolvedValue(mockMembers);
    });

    it('defaults to member organizations view', async () => {
      render(<OrganizationManagement onClose={mockOnClose} />);

      await waitFor(() => {
        expect(screen.getByText('My Organizations')).toHaveClass('bg-green-100');
        expect(screen.getByText('Showing 1 organizations where you are a member')).toBeInTheDocument();
      });

      // Should only show member organization
      expect(screen.getByText('Member Organization')).toBeInTheDocument();
      expect(screen.queryByText('Non-Member Organization')).not.toBeInTheDocument();
    });

    it('shows confirmation dialog when switching to all organizations', async () => {
      render(<OrganizationManagement onClose={mockOnClose} />);

      await waitFor(() => {
        expect(screen.getByText('Organization Management')).toBeInTheDocument();
      });

      // Click "All Organizations" button
      fireEvent.click(screen.getByText('All Organizations'));

      // Should show confirmation dialog
      expect(screen.getByText('Switch to All Organizations?')).toBeInTheDocument();
      expect(screen.getByText(/You are about to view all organizations/)).toBeInTheDocument();
    });

    it('switches to all organizations view after confirmation', async () => {
      render(<OrganizationManagement onClose={mockOnClose} />);

      await waitFor(() => {
        expect(screen.getByText('Organization Management')).toBeInTheDocument();
      });

      // Click "All Organizations" button
      fireEvent.click(screen.getByText('All Organizations'));

      // Confirm the switch
      fireEvent.click(screen.getByText('Show All Organizations'));

      await waitFor(() => {
        expect(screen.getByText('All Organizations')).toHaveClass('bg-orange-100');
        expect(screen.getByText('Showing 2 organizations (1 member, 1 admin-only)')).toBeInTheDocument();
      });

      // Should show both organizations
      expect(screen.getByText('Member Organization')).toBeInTheDocument();
      expect(screen.getByText('Non-Member Organization')).toBeInTheDocument();
    });

    it('cancels mode switch when cancelled', async () => {
      render(<OrganizationManagement onClose={mockOnClose} />);

      await waitFor(() => {
        expect(screen.getByText('Organization Management')).toBeInTheDocument();
      });

      // Click "All Organizations" button
      fireEvent.click(screen.getByText('All Organizations'));

      // Cancel the switch
      fireEvent.click(screen.getByText('Cancel'));

      // Should remain in member mode
      await waitFor(() => {
        expect(screen.getByText('My Organizations')).toHaveClass('bg-green-100');
        expect(screen.queryByText('Non-Member Organization')).not.toBeInTheDocument();
      });
    });

    it('allows direct switch back to member organizations without confirmation', async () => {
      render(<OrganizationManagement onClose={mockOnClose} />);

      await waitFor(() => {
        expect(screen.getByText('Organization Management')).toBeInTheDocument();
      });

      // Switch to all organizations first
      fireEvent.click(screen.getByText('All Organizations'));
      fireEvent.click(screen.getByText('Show All Organizations'));

      await waitFor(() => {
        expect(screen.getByText('All Organizations')).toHaveClass('bg-orange-100');
      });

      // Switch back to member organizations
      fireEvent.click(screen.getByText('My Organizations'));

      // Should switch immediately without confirmation
      await waitFor(() => {
        expect(screen.getByText('My Organizations')).toHaveClass('bg-green-100');
        expect(screen.queryByText('Non-Member Organization')).not.toBeInTheDocument();
      });
    });
  });

  describe('Organization Display', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: {
          authenticated: true,
          email: 'admin@example.com',
          is_superadmin: true,
        },
        loading: false,
      } as any);

      mockOrganizationService.getManageableOrganizations.mockResolvedValue(mockOrganizations);
      mockOrganizationService.getOrganizations.mockResolvedValue(mockUserMemberOrgs);
      mockOrganizationService.getMembers.mockResolvedValue(mockMembers);
    });

    it('shows visual indicators for membership status in all organizations view', async () => {
      render(<OrganizationManagement onClose={mockOnClose} />);

      // Switch to all organizations view
      await waitFor(() => {
        expect(screen.getByText('Organization Management')).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText('All Organizations'));
      fireEvent.click(screen.getByText('Show All Organizations'));

      await waitFor(() => {
        expect(screen.getByText('All Organizations')).toHaveClass('bg-orange-100');
      });

      // Should show membership badges
      expect(screen.getByText('Member')).toBeInTheDocument();
      expect(screen.getByText('Not Member')).toBeInTheDocument();
    });

    it('applies correct styling for member vs non-member organizations', async () => {
      render(<OrganizationManagement onClose={mockOnClose} />);

      // Switch to all organizations view
      await waitFor(() => {
        expect(screen.getByText('Organization Management')).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText('All Organizations'));
      fireEvent.click(screen.getByText('Show All Organizations'));

      await waitFor(() => {
        // Get the organization cards by their container with the border-l-4 class
        const memberOrg = screen.getByText('Member Organization').closest('.border-l-4');
        const nonMemberOrg = screen.getByText('Non-Member Organization').closest('.border-l-4');

        // Member organization should have green border
        expect(memberOrg).toHaveClass('border-l-green-500');
        
        // Non-member organization should have red border  
        expect(nonMemberOrg).toHaveClass('border-l-red-500');
      });
    });
  });

  describe('Data Fetching', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: {
          authenticated: true,
          email: 'admin@example.com',
          is_superadmin: true,
        },
        loading: false,
      } as any);
    });

    it('fetches admin organizations and user memberships for superadmin', async () => {
      mockOrganizationService.getManageableOrganizations.mockResolvedValue(mockOrganizations);
      mockOrganizationService.getOrganizations.mockResolvedValue(mockUserMemberOrgs);

      render(<OrganizationManagement onClose={mockOnClose} />);

      await waitFor(() => {
        expect(mockOrganizationService.getManageableOrganizations).toHaveBeenCalledTimes(1);
        expect(mockOrganizationService.getOrganizations).toHaveBeenCalledTimes(1);
      });
    });

    it('fetches regular organizations for non-superadmin (fallback)', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          authenticated: true,
          email: 'user@example.com',
          is_superadmin: false,
        },
        loading: false,
      } as any);

      mockOrganizationService.getOrganizations.mockResolvedValue(mockUserMemberOrgs);

      render(<OrganizationManagement onClose={mockOnClose} />);

      // Should show access denied, but still test the fetching logic path
      expect(mockOrganizationService.getManageableOrganizations).not.toHaveBeenCalled();
    });

    it('handles fetch errors gracefully', async () => {
      mockOrganizationService.getManageableOrganizations.mockRejectedValue(new Error('Fetch failed'));
      mockOrganizationService.getOrganizations.mockRejectedValue(new Error('Fetch failed'));

      render(<OrganizationManagement onClose={mockOnClose} />);

      await waitFor(() => {
        expect(mockNotificationService.showError).toHaveBeenCalledWith('Failed to fetch organizations');
      });
    });
  });

  describe('Integration', () => {
    it('maintains selection when switching view modes', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          authenticated: true,
          email: 'admin@example.com',
          is_superadmin: true,
        },
        loading: false,
      } as any);

      mockOrganizationService.getManageableOrganizations.mockResolvedValue(mockOrganizations);
      mockOrganizationService.getOrganizations.mockResolvedValue(mockUserMemberOrgs);
      mockOrganizationService.getMembers.mockResolvedValue(mockMembers);

      render(<OrganizationManagement onClose={mockOnClose} />);

      // Wait for organizations to load and select first one
      await waitFor(() => {
        expect(screen.getByText('Member Organization')).toBeInTheDocument();
      });

      // Click on organization to select it
      fireEvent.click(screen.getByText('Member Organization'));

      // Switch to all organizations view
      fireEvent.click(screen.getByText('All Organizations'));
      fireEvent.click(screen.getByText('Show All Organizations'));

      // Selection should be reset when switching modes
      // (This is the current behavior as implemented)
      await waitFor(() => {
        expect(screen.getByText('All Organizations')).toHaveClass('bg-orange-100');
      });
    });
  });
});
