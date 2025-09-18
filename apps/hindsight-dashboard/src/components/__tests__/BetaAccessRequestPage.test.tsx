import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import BetaAccessRequestPage from '../BetaAccessRequestPage';
import { apiFetch } from '../../api/http';
import { useAuth } from '../../context/AuthContext';
import notificationService from '../../services/notificationService';

jest.mock('../../api/http', () => ({
  apiFetch: jest.fn(),
}));

jest.mock('../../context/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: {
    showSuccess: jest.fn(),
    showWarning: jest.fn(),
    showError: jest.fn(),
    showNetworkError: jest.fn(),
  },
}));

const mockApiFetch = apiFetch as jest.Mock;
const mockUseAuth = useAuth as jest.Mock;
const mockNotification = notificationService as jest.Mocked<typeof notificationService>;

const createAuthState = () => ({
  user: { authenticated: true, email: 'test@example.com' },
  loading: false,
  guest: false,
  enterGuestMode: jest.fn(),
  exitGuestMode: jest.fn(),
  refresh: jest.fn(),
});

let authState: ReturnType<typeof createAuthState>;

const setupAuth = (overrides: Partial<ReturnType<typeof createAuthState>> = {}) => {
  const state = { ...createAuthState(), ...overrides };
  mockUseAuth.mockReturnValue(state);
  authState = state as ReturnType<typeof createAuthState>;
  return state;
};

describe('BetaAccessRequestPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupAuth();
  });

  test('renders the request form correctly', () => {
    render(<BetaAccessRequestPage />);

    expect(screen.getByText('Join the Beta')).toBeInTheDocument();
    expect(screen.getByText('Request access to the Hindsight AI beta program')).toBeInTheDocument();
    const emailInput = screen.getByLabelText(/email address/i) as HTMLInputElement;
    expect(emailInput).toBeInTheDocument();
    expect(emailInput).toHaveAttribute('readonly');
    expect(emailInput.value).toBe('test@example.com');
    expect(screen.getByRole('button', { name: /request beta access/i })).toBeInTheDocument();
    expect(screen.getByText('Beta Program Disclaimer')).toBeInTheDocument();
    expect(screen.getByLabelText(/I understand and accept the beta program disclaimer/i)).toBeInTheDocument();
  });

  test('submits request successfully and shows success state', async () => {
    const mockResponse = { success: true, request_id: '123' };
    mockApiFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => mockResponse,
    });

    render(<BetaAccessRequestPage />);

    const disclaimerCheckbox = screen.getByLabelText(/I understand and accept the beta program disclaimer/i);
    const submitButton = screen.getByRole('button', { name: /request beta access/i });

    fireEvent.click(disclaimerCheckbox);
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Request Submitted!')).toBeInTheDocument();
      expect(screen.getByText('Your request to join the Hindsight AI beta has been submitted successfully.')).toBeInTheDocument();
    });

    expect(mockApiFetch).toHaveBeenCalledWith('/beta-access/request', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      noScope: true,
      body: JSON.stringify({ email: 'test@example.com' }),
    });
    expect(mockNotification.showSuccess).toHaveBeenCalledWith('Beta access request sent! Check your email for confirmation.');
    expect(authState.refresh).toHaveBeenCalled();
    expect(mockNotification.showWarning).not.toHaveBeenCalled();
  });

  test('shows error message when request fails', async () => {
    const mockResponse = { success: false, message: 'Email already registered' };
    mockApiFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => mockResponse,
    });

    render(<BetaAccessRequestPage />);

    const disclaimerCheckbox = screen.getByLabelText(/I understand and accept the beta program disclaimer/i);
    const submitButton = screen.getByRole('button', { name: /request beta access/i });

    fireEvent.click(disclaimerCheckbox);
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Failed to submit request. Please try again.')).toBeInTheDocument();
    });

    expect(mockNotification.showError).toHaveBeenCalledWith('Unable to submit your beta access request. Please try again.');
    expect(mockNotification.showWarning).not.toHaveBeenCalled();
    expect(mockNotification.showSuccess).not.toHaveBeenCalled();
  });

  test('shows warning for duplicate request', async () => {
    mockApiFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Request already exists or accepted.' }),
    });

    render(<BetaAccessRequestPage />);

    const disclaimerCheckbox = screen.getByLabelText(/I understand and accept the beta program disclaimer/i);
    const submitButton = screen.getByRole('button', { name: /request beta access/i });

    fireEvent.click(disclaimerCheckbox);
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('You have already requested beta access. Please wait for approval.')).toBeInTheDocument();
    });

    expect(mockNotification.showWarning).toHaveBeenCalledWith('You have already requested beta access. We will reach out once it is reviewed.');
    expect(mockNotification.showSuccess).not.toHaveBeenCalled();
    expect(mockNotification.showError).not.toHaveBeenCalled();
  });

  test('shows network error message when fetch fails', async () => {
    mockApiFetch.mockRejectedValueOnce(new Error('Network error'));

    render(<BetaAccessRequestPage />);

    const disclaimerCheckbox = screen.getByLabelText(/I understand and accept the beta program disclaimer/i);
    const submitButton = screen.getByRole('button', { name: /request beta access/i });

    fireEvent.click(disclaimerCheckbox);
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Network error. Please check your connection and try again.')).toBeInTheDocument();
    });

    expect(mockNotification.showNetworkError).toHaveBeenCalled();
    expect(mockNotification.showSuccess).not.toHaveBeenCalled();
  });

  test('prevents form submission when disclaimer is not accepted', async () => {
    render(<BetaAccessRequestPage />);

    const submitButton = screen.getByRole('button', { name: /request beta access/i });

    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('You must accept the beta program disclaimer to proceed')).toBeInTheDocument();
    });

    expect(mockApiFetch).not.toHaveBeenCalled();
    expect(mockNotification.showSuccess).not.toHaveBeenCalled();
    expect(mockNotification.showWarning).not.toHaveBeenCalled();
  });

  test('disables submit button while loading', async () => {
    mockApiFetch.mockImplementationOnce(
      () => new Promise(resolve => setTimeout(() => resolve({
        ok: true,
        status: 201,
        json: async () => ({ success: true }),
      }), 100))
    );

    render(<BetaAccessRequestPage />);

    const disclaimerCheckbox = screen.getByLabelText(/I understand and accept the beta program disclaimer/i);
    const submitButton = screen.getByRole('button', { name: /request beta access/i });

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
    mockApiFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => mockResponse,
    });

    render(<BetaAccessRequestPage />);

    // Submit first request
    const disclaimerCheckbox = screen.getByLabelText(/I understand and accept the beta program disclaimer/i);
    const submitButton = screen.getByRole('button', { name: /request beta access/i });

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
