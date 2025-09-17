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

    expect(screen.getByText('Superadmin access')).toBeInTheDocument();
    expect(screen.getByText('Beta access admin')).toBeInTheDocument();
    expect(screen.getByText('Beta access status')).toBeInTheDocument();
    expect(screen.getByText('accepted')).toBeInTheDocument();
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

    expect(screen.queryByText('Superadmin access')).not.toBeInTheDocument();
    expect(screen.queryByText('Beta access admin')).not.toBeInTheDocument();
    expect(screen.getByText('No elevated privileges')).toBeInTheDocument();
    expect(screen.getByText('Beta access status')).toBeInTheDocument();
    expect(screen.getByText('not requested')).toBeInTheDocument();
  });
});
