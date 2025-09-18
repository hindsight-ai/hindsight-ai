import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import BetaAccessPendingPage from '../BetaAccessPendingPage';

// Mock window.location.reload
const mockReload = jest.fn();
Object.defineProperty(window, 'location', {
  value: { reload: mockReload },
  writable: true,
});

describe('BetaAccessPendingPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders the pending page correctly', () => {
    render(<BetaAccessPendingPage />);

    expect(screen.getByText('Beta Access Pending')).toBeInTheDocument();
    expect(screen.getByText('Your request to join the Hindsight AI beta has been received and is being reviewed.')).toBeInTheDocument();
    expect(screen.getByText('Check your email')).toBeInTheDocument();
    expect(screen.getByText('Requests are typically reviewed within 24 hours.')).toBeInTheDocument();
  });

  test('displays refresh button', () => {
    render(<BetaAccessPendingPage />);

    const refreshButton = screen.getByRole('button', { name: /check status/i });
    expect(refreshButton).toBeInTheDocument();
  });

  test('refresh button calls window.location.reload', () => {
    render(<BetaAccessPendingPage />);

    const refreshButton = screen.getByRole('button', { name: /check status/i });
    fireEvent.click(refreshButton);

    expect(mockReload).toHaveBeenCalledTimes(1);
  });

  test('has correct styling classes', () => {
    render(<BetaAccessPendingPage />);

    // Check main container
    const mainDiv = screen.getByText('Beta Access Pending').closest('.min-h-screen');
    expect(mainDiv).toHaveClass('bg-gradient-to-br from-blue-50 to-indigo-100');

    // Check card container
    const cardDiv = screen.getByText('Beta Access Pending').closest('.bg-white') as HTMLElement;
    expect(cardDiv).toHaveClass('max-w-md');
    expect(cardDiv).toHaveClass('w-full');
    expect(cardDiv).toHaveClass('bg-white');
  });
});