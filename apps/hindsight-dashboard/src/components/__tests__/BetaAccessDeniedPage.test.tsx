import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import BetaAccessDeniedPage from '../BetaAccessDeniedPage';

describe('BetaAccessDeniedPage', () => {
  test('renders the denied page correctly', () => {
    render(<BetaAccessDeniedPage />);

    expect(screen.getByText('Access Denied')).toBeInTheDocument();
    expect(screen.getByText('Your request to join the Hindsight AI beta program has been denied.')).toBeInTheDocument();
    expect(screen.getByText('Contact Support')).toBeInTheDocument();
    expect(screen.getByText('If you believe this decision was made in error, please contact our support team.')).toBeInTheDocument();
  });

  test('displays the X circle icon', () => {
    render(<BetaAccessDeniedPage />);

    const xIcon = document.querySelector('svg');
    expect(xIcon).toBeInTheDocument();
    expect(xIcon).toHaveAttribute('stroke', 'currentColor');
  });

  test('displays support email link', () => {
    render(<BetaAccessDeniedPage />);

    const emailLink = screen.getByRole('link', { name: /email support/i });
    expect(emailLink).toBeInTheDocument();
    expect(emailLink).toHaveAttribute('href', 'mailto:support@hindsight-ai.com?subject=Beta Access Denial Appeal&body=Hello,%0A%0AI would like to appeal my beta access denial decision.%0A%0AMy email: [your email]%0AReason for appeal: [please explain]%0A%0AThank you.');
  });

  test('displays the footer text', () => {
    render(<BetaAccessDeniedPage />);

    expect(screen.getByText('Hindsight AI - Memory Intelligence Hub')).toBeInTheDocument();
  });

  test('has correct styling classes', () => {
    const { container } = render(<BetaAccessDeniedPage />);

    // Check main container
    const mainDiv = container.firstChild as HTMLElement;
    expect(mainDiv).toHaveClass('min-h-screen');
    expect(mainDiv).toHaveClass('bg-gradient-to-br');
    expect(mainDiv).toHaveClass('flex');
    expect(mainDiv).toHaveClass('items-center');
    expect(mainDiv).toHaveClass('justify-center');
    expect(mainDiv).toHaveClass('p-4');

    // Check card container
    const cardDiv = screen.getByText('Access Denied').closest('.bg-white') as HTMLElement;
    expect(cardDiv).toHaveClass('max-w-md');
    expect(cardDiv).toHaveClass('w-full');
    expect(cardDiv).toHaveClass('bg-white');
    expect(cardDiv).toHaveClass('rounded-lg');
    expect(cardDiv).toHaveClass('shadow-xl');
    expect(cardDiv).toHaveClass('p-8');
    expect(cardDiv).toHaveClass('text-center');

    // Check email link styling
    const emailLink = screen.getByRole('link', { name: /email support/i }) as HTMLElement;
    expect(emailLink).toHaveClass('inline-flex');
    expect(emailLink).toHaveClass('bg-red-600');
    expect(emailLink).toHaveClass('text-white');
  });
});
