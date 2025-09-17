import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import BetaAccessGrantConfirmationPage from '../BetaAccessGrantConfirmationPage';

describe('BetaAccessGrantConfirmationPage', () => {
  const renderWithRoute = (initialEntry: string) =>
    render(
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/beta-access/review/granted" element={<BetaAccessGrantConfirmationPage />} />
        </Routes>
      </MemoryRouter>
    );

  it('displays the granted email when provided in query params', () => {
    renderWithRoute('/beta-access/review/granted?email=tester%40example.com');
    expect(screen.getByText(/Beta Access Granted/i)).toBeInTheDocument();
    expect(screen.getAllByText(/tester@example.com/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/has been approved/i).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: /View Pending Requests/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Go to Dashboard/i })).toBeInTheDocument();
  });

  it('shows already granted messaging when status=already', () => {
    renderWithRoute('/beta-access/review/granted?email=alice%40example.com&status=already');
    expect(screen.getByText(/Access Already Granted/i)).toBeInTheDocument();
    expect(screen.getByText(/alice@example.com/i)).toBeInTheDocument();
    expect(screen.getByText(/was already granted earlier/i)).toBeInTheDocument();
  });

  it('falls back to generic message when email missing', () => {
    renderWithRoute('/beta-access/review/granted');
    expect(screen.getByText(/Beta Access Granted/i)).toBeInTheDocument();
    expect(screen.getByText(/The beta access request has been approved/i)).toBeInTheDocument();
  });
});
