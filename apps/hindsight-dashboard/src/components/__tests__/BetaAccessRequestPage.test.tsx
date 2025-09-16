import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import BetaAccessRequestPage from '../BetaAccessRequestPage';

// Mock fetch globally
global.fetch = jest.fn();

describe('BetaAccessRequestPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders the request form correctly', () => {
    render(<BetaAccessRequestPage />);

    expect(screen.getByText('Join the Beta')).toBeInTheDocument();
    expect(screen.getByText('Request access to the Hindsight AI beta program')).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /request beta access/i })).toBeInTheDocument();
    expect(screen.getByText('Beta Program Disclaimer')).toBeInTheDocument();
    expect(screen.getByLabelText(/I understand and accept the beta program disclaimer/i)).toBeInTheDocument();
  });

  test('submits request successfully and shows success state', async () => {
    const mockResponse = { success: true, request_id: '123' };
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<BetaAccessRequestPage />);

    const emailInput = screen.getByLabelText(/email address/i);
    const disclaimerCheckbox = screen.getByLabelText(/I understand and accept the beta program disclaimer/i);
    const submitButton = screen.getByRole('button', { name: /request beta access/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.click(disclaimerCheckbox);
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Request Submitted!')).toBeInTheDocument();
      expect(screen.getByText('Your request to join the Hindsight AI beta has been submitted successfully.')).toBeInTheDocument();
    });

    expect(global.fetch).toHaveBeenCalledWith('/api/beta-access/request', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ email: 'test@example.com' }),
    });
  });

  test('shows error message when request fails', async () => {
    const mockResponse = { success: false, message: 'Email already registered' };
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => mockResponse,
    });

    render(<BetaAccessRequestPage />);

    const emailInput = screen.getByLabelText(/email address/i);
    const disclaimerCheckbox = screen.getByLabelText(/I understand and accept the beta program disclaimer/i);
    const submitButton = screen.getByRole('button', { name: /request beta access/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.click(disclaimerCheckbox);
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Failed to submit request. Please try again.')).toBeInTheDocument();
    });
  });

  test('shows network error message when fetch fails', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    render(<BetaAccessRequestPage />);

    const emailInput = screen.getByLabelText(/email address/i);
    const disclaimerCheckbox = screen.getByLabelText(/I understand and accept the beta program disclaimer/i);
    const submitButton = screen.getByRole('button', { name: /request beta access/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.click(disclaimerCheckbox);
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Network error. Please check your connection and try again.')).toBeInTheDocument();
    });
  });

  test('prevents form submission when disclaimer is not accepted', async () => {
    render(<BetaAccessRequestPage />);

    const emailInput = screen.getByLabelText(/email address/i);
    const submitButton = screen.getByRole('button', { name: /request beta access/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('You must accept the beta program disclaimer to proceed')).toBeInTheDocument();
    });

    expect(global.fetch).not.toHaveBeenCalled();
  });

  test('disables submit button while loading', async () => {
    (global.fetch as jest.Mock).mockImplementationOnce(
      () => new Promise(resolve => setTimeout(() => resolve({
        ok: true,
        json: async () => ({ success: true }),
      }), 100))
    );

    render(<BetaAccessRequestPage />);

    const emailInput = screen.getByLabelText(/email address/i);
    const disclaimerCheckbox = screen.getByLabelText(/I understand and accept the beta program disclaimer/i);
    const submitButton = screen.getByRole('button', { name: /request beta access/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.click(disclaimerCheckbox);
    fireEvent.click(submitButton);

    // Button should be disabled during loading
    expect(submitButton).toBeDisabled();
    expect(screen.getByText('Submitting...')).toBeInTheDocument();

    // After successful submission, component transitions to success state
    await waitFor(() => {
      expect(screen.getByText('Request Submitted!')).toBeInTheDocument();
    });
  });

  test('shows success state after successful submission', async () => {
    const mockResponse = { success: true };
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<BetaAccessRequestPage />);

    // Submit first request
    const emailInput = screen.getByLabelText(/email address/i);
    const disclaimerCheckbox = screen.getByLabelText(/I understand and accept the beta program disclaimer/i);
    const submitButton = screen.getByRole('button', { name: /request beta access/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.click(disclaimerCheckbox);
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Request Submitted!')).toBeInTheDocument();
      expect(screen.getByText('Your request to join the Hindsight AI beta has been submitted successfully.')).toBeInTheDocument();
    });

    // Success state should persist
    expect(screen.getByText('Check your email')).toBeInTheDocument();
    expect(screen.getByText('Your request will be reviewed within 24 hours.')).toBeInTheDocument();
  });
});
