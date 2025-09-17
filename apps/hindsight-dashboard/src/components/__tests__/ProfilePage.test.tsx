import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { jest } from '@jest/globals';

import ProfilePage from '../ProfilePage';
import { useAuth } from '../../context/AuthContext';

jest.mock('../../context/AuthContext');

const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

const baseAuthValue = {
  loading: false,
  guest: false,
  enterGuestMode: jest.fn(),
  exitGuestMode: jest.fn(),
  refresh: jest.fn(),
};

describe('ProfilePage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderWithUser = (user: any) => {
    mockUseAuth.mockReturnValue({
      ...baseAuthValue,
      user,
    } as any);

    render(<ProfilePage />);
  };

  it('shows enabled privilege indicators when flags are present', () => {
    renderWithUser({
      authenticated: true,
      email: 'admin@example.com',
      display_name: 'Admin User',
      is_superadmin: true,
      beta_access_admin: true,
      beta_access_status: 'accepted',
    });

    expect(screen.getByRole('heading', { name: 'Profile' })).toBeInTheDocument();

    const superadminRow = screen.getByText('Superadmin access').closest('div');
    expect(superadminRow).toHaveTextContent('Enabled');

    const betaAdminRow = screen.getByText('Beta access admin').closest('div');
    expect(betaAdminRow).toHaveTextContent('Enabled');

    const betaStatusRow = screen.getByText('Beta access status').closest('div');
    expect(betaStatusRow).toHaveTextContent('accepted');
  });

  it('shows disabled privilege indicators when flags are absent', () => {
    renderWithUser({
      authenticated: true,
      email: 'member@example.com',
      display_name: 'Member User',
      is_superadmin: false,
      beta_access_admin: false,
      beta_access_status: 'not_requested',
    });

    const superadminRow = screen.getByText('Superadmin access').closest('div');
    expect(superadminRow).toHaveTextContent('Not granted');

    const betaAdminRow = screen.getByText('Beta access admin').closest('div');
    expect(betaAdminRow).toHaveTextContent('Not granted');

    const betaStatusRow = screen.getByText('Beta access status').closest('div');
    expect(betaStatusRow).toHaveTextContent('not requested');
  });
});
