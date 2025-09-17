import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { jest } from '@jest/globals';

import UserAccountButton from '../UserAccountButton';
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

describe('UserAccountButton', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderWithUser = (user: any) => {
    mockUseAuth.mockReturnValue({
      ...baseAuthValue,
      user,
    } as any);

    render(<UserAccountButton />);

    const toggleButton = screen.getAllByRole('button')[0];
    fireEvent.click(toggleButton);
  };

  it('displays superadmin and beta admin pills along with profile entry', () => {
    renderWithUser({
      authenticated: true,
      email: 'admin@example.com',
      is_superadmin: true,
      beta_access_admin: true,
    });

    expect(screen.getByText('Superadmin')).toBeInTheDocument();
    expect(screen.getByText('Beta Admin')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Profile' })).toBeInTheDocument();
    expect(screen.queryByText('Edit Profile')).not.toBeInTheDocument();
  });

  it('omits privilege pills when flags are not set', () => {
    renderWithUser({
      authenticated: true,
      email: 'member@example.com',
      is_superadmin: false,
      beta_access_admin: false,
    });

    expect(screen.queryByText('Superadmin')).not.toBeInTheDocument();
    expect(screen.queryByText('Beta Admin')).not.toBeInTheDocument();
  });
});
