/**
 * Direct tests for OrganizationInvitationsPanel — closes the gap from #80
 * (god-component split) where the lifted invitation table had zero direct
 * coverage. The OrganizationManagement.test.tsx suite never exercised the
 * invitation tab; tests here pin the resend/revoke/filter/audit-modal flows.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import OrganizationInvitationsPanel from '../OrganizationInvitationsPanel';
import type { Organization, OrganizationInvitation } from '../../api/organizationService';

jest.mock('../../api/organizationService', () => ({
  __esModule: true,
  default: {
    resendInvitation: jest.fn(),
    revokeInvitation: jest.fn(),
  },
}));

jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: {
    showSuccess: jest.fn(),
    showInfo: jest.fn(),
    showError: jest.fn(),
  },
}));

jest.mock('../AuditLogs', () => ({
  __esModule: true,
  default: ({ invitationId, orgId }: { invitationId: string; orgId: string }) => (
    <div data-testid="audit-logs-stub">audit:{orgId}:{invitationId}</div>
  ),
}));

import organizationService from '../../api/organizationService';
import notificationService from '../../services/notificationService';

const mockOrg: Organization = {
  id: 'org-1',
  name: 'Acme',
  slug: 'acme',
} as Organization;

const mockInvitations: OrganizationInvitation[] = [
  {
    id: 'inv-pending',
    email: 'pending@example.com',
    role: 'editor',
    status: 'pending',
    created_at: '2026-04-01T00:00:00Z',
    expires_at: '2026-05-01T00:00:00Z',
  } as OrganizationInvitation,
  {
    id: 'inv-accepted',
    email: 'accepted@example.com',
    role: 'viewer',
    status: 'accepted',
    created_at: '2026-04-01T00:00:00Z',
    expires_at: '2026-05-01T00:00:00Z',
  } as OrganizationInvitation,
];

const mockCounts = { pending: 1, accepted: 1, revoked: 0, expired: 0 };

const renderPanel = (overrides: Partial<React.ComponentProps<typeof OrganizationInvitationsPanel>> = {}) => {
  const onFilterChange = jest.fn();
  const onRefreshInvitations = jest.fn().mockResolvedValue(undefined);
  const onRefreshCounts = jest.fn().mockResolvedValue(undefined);
  const props = {
    selectedOrg: mockOrg,
    invitations: mockInvitations,
    invitationFilter: 'pending' as const,
    invCounts: mockCounts,
    onFilterChange,
    onRefreshInvitations,
    onRefreshCounts,
    ...overrides,
  };
  const utils = render(<OrganizationInvitationsPanel {...props} />);
  return { ...utils, onFilterChange, onRefreshInvitations, onRefreshCounts };
};

describe('OrganizationInvitationsPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the invitation table with rows from the prop', () => {
    renderPanel();
    expect(screen.getByText('Invitations')).toBeInTheDocument();
    expect(screen.getByText('pending@example.com')).toBeInTheDocument();
    expect(screen.getByText('accepted@example.com')).toBeInTheDocument();
  });

  it('shows the empty state when no invitations are passed', () => {
    renderPanel({ invitations: [] });
    expect(screen.getByText('No invitations found.')).toBeInTheDocument();
  });

  it('displays counts pinned in the header chip', () => {
    renderPanel({ invCounts: { pending: 7, accepted: 3, revoked: 2, expired: 5 } });
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('clicking a filter tab calls onFilterChange with the new filter', () => {
    const { onFilterChange } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: 'Accepted' }));
    expect(onFilterChange).toHaveBeenCalledWith('accepted');
  });

  it('Resend button is disabled for non-pending invitations', () => {
    renderPanel();
    // Two rows: pending (resend enabled) + accepted (resend disabled)
    const resendButtons = screen.getAllByRole('button', { name: 'Resend' });
    expect(resendButtons).toHaveLength(2);
    expect(resendButtons[0]).not.toBeDisabled();   // pending row
    expect(resendButtons[1]).toBeDisabled();       // accepted row
  });

  it('clicking Resend on a pending invite calls service + refreshes + shows success', async () => {
    (organizationService.resendInvitation as jest.Mock).mockResolvedValueOnce({});
    const { onRefreshInvitations, onRefreshCounts } = renderPanel();
    fireEvent.click(screen.getAllByRole('button', { name: 'Resend' })[0]);
    await waitFor(() => {
      expect(organizationService.resendInvitation).toHaveBeenCalledWith('org-1', 'inv-pending');
    });
    expect(notificationService.showSuccess).toHaveBeenCalledWith('Invitation resent');
    expect(onRefreshInvitations).toHaveBeenCalled();
    expect(onRefreshCounts).toHaveBeenCalled();
  });

  it('clicking Resend shows error toast when service throws', async () => {
    (organizationService.resendInvitation as jest.Mock).mockRejectedValueOnce(new Error('boom'));
    renderPanel();
    fireEvent.click(screen.getAllByRole('button', { name: 'Resend' })[0]);
    await waitFor(() => {
      expect(notificationService.showError).toHaveBeenCalledWith('Failed to resend: boom');
    });
  });

  it('clicking Revoke calls service + refreshes + shows info toast', async () => {
    (organizationService.revokeInvitation as jest.Mock).mockResolvedValueOnce(undefined);
    const { onRefreshInvitations, onRefreshCounts } = renderPanel();
    fireEvent.click(screen.getAllByRole('button', { name: 'Revoke' })[0]);
    await waitFor(() => {
      expect(organizationService.revokeInvitation).toHaveBeenCalledWith('org-1', 'inv-pending');
    });
    expect(notificationService.showInfo).toHaveBeenCalledWith('Invitation revoked');
    expect(onRefreshInvitations).toHaveBeenCalled();
    expect(onRefreshCounts).toHaveBeenCalled();
  });

  it('clicking Revoke shows error toast when service throws', async () => {
    (organizationService.revokeInvitation as jest.Mock).mockRejectedValueOnce(new Error('nope'));
    renderPanel();
    fireEvent.click(screen.getAllByRole('button', { name: 'Revoke' })[0]);
    await waitFor(() => {
      expect(notificationService.showError).toHaveBeenCalledWith('Failed to revoke: nope');
    });
  });

  it('View Audit opens the modal with the audit-logs stub for the right invitation', () => {
    renderPanel();
    fireEvent.click(screen.getAllByRole('button', { name: 'View Audit' })[0]);
    const stub = screen.getByTestId('audit-logs-stub');
    expect(stub).toHaveTextContent('audit:org-1:inv-pending');
  });

  it('audit modal closes when the × button is clicked', () => {
    renderPanel();
    fireEvent.click(screen.getAllByRole('button', { name: 'View Audit' })[0]);
    expect(screen.getByTestId('audit-logs-stub')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '×' }));
    expect(screen.queryByTestId('audit-logs-stub')).not.toBeInTheDocument();
  });
});
