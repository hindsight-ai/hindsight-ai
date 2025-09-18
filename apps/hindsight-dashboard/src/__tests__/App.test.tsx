import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from '../App';

// Mock all the components to avoid complex dependencies
jest.mock('../components/Layout', () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div data-testid="layout">{children}</div>,
}));

jest.mock('../components/Dashboard', () => ({
  __esModule: true,
  default: () => <div data-testid="dashboard">Dashboard</div>,
}));

jest.mock('../components/LoginPage', () => ({
  __esModule: true,
  default: () => <div data-testid="login-page">Login Page</div>,
}));

jest.mock('../components/BetaAccessRequestPage', () => ({
  __esModule: true,
  default: () => <div data-testid="beta-access-request">Beta Access Request</div>,
}));

jest.mock('../components/BetaAccessPendingPage', () => ({
  __esModule: true,
  default: () => <div data-testid="beta-access-pending">Beta Access Pending</div>,
}));

jest.mock('../components/BetaAccessDeniedPage', () => ({
  __esModule: true,
  default: () => <div data-testid="beta-access-denied">Beta Access Denied</div>,
}));

// Mock AuthContext
jest.mock('../context/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="auth-provider">{children}</div>,
  useAuth: jest.fn(),
}));

// Mock other contexts
jest.mock('../context/OrgContext', () => ({
  OrgProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="org-provider">{children}</div>,
}));

jest.mock('../context/OrganizationContext', () => ({
  OrganizationProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="organization-provider">{children}</div>,
}));

jest.mock('../context/NotificationContext', () => ({
  NotificationProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="notification-provider">{children}</div>,
}));

// Mock services
jest.mock('../api/organizationService', () => ({
  acceptInvitation: jest.fn(),
  declineInvitation: jest.fn(),
}));

jest.mock('../api/betaAccessService', () => ({
  __esModule: true,
  default: {
    reviewWithToken: jest.fn(),
  },
}));

jest.mock('../services/notificationService', () => ({
  showSuccess: jest.fn(),
  showWarning: jest.fn(),
  showError: jest.fn(),
  showInfo: jest.fn(),
}));

// Mock NotificationContainer
jest.mock('../components/NotificationContainer', () => ({
  __esModule: true,
  default: () => <div data-testid="notification-container" />,
}));

// Mock DebugPanel
jest.mock('../components/DebugPanel', () => ({
  __esModule: true,
  default: ({ visible }: { visible: boolean }) => visible ? <div data-testid="debug-panel">Debug Panel</div> : null,
}));

// Mock AboutModal
jest.mock('../components/AboutModal', () => ({
  __esModule: true,
  default: ({ isOpen }: { isOpen: boolean }) => isOpen ? <div data-testid="about-modal">About Modal</div> : null,
}));

describe('App Beta Access Routing', () => {
  const mockUseAuth = require('../context/AuthContext').useAuth;
  const betaAccessServiceMock = require('../api/betaAccessService').default;
  const notifications = require('../services/notificationService');

  beforeEach(() => {
    jest.clearAllMocks();
    // Mock window methods
    delete (window as any).location;
    window.location = { replace: jest.fn(), href: '' } as any;
    (window as any).scrollTo = jest.fn();
    betaAccessServiceMock.reviewWithToken.mockReset();
    notifications.showSuccess.mockReset();
    notifications.showInfo.mockReset();
    notifications.showWarning.mockReset();
    notifications.showError.mockReset();
  });

  test('renders login page when on /login route', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      loading: false,
      guest: false,
    });

    // Mock window.location.pathname
    Object.defineProperty(window, 'location', {
      value: { pathname: '/login', search: '', replace: jest.fn(), href: '' },
      writable: true,
    });

  render(<App />);

    expect(screen.getByTestId('login-page')).toBeInTheDocument();
  });

  test('renders beta access request page when on /beta-access/request route', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      loading: false,
      guest: false,
    });

    Object.defineProperty(window, 'location', {
      value: { pathname: '/beta-access/request', search: '', replace: jest.fn(), href: '' },
      writable: true,
    });

  render(<App />);

    expect(screen.getByTestId('beta-access-request')).toBeInTheDocument();
  });

  test('renders beta access pending page when on /beta-access/pending route', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      loading: false,
      guest: false,
    });

    Object.defineProperty(window, 'location', {
      value: { pathname: '/beta-access/pending', search: '', replace: jest.fn(), href: '' },
      writable: true,
    });

  render(<App />);

    expect(screen.getByTestId('beta-access-pending')).toBeInTheDocument();
  });

  test('renders beta access denied page when on /beta-access/denied route', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      loading: false,
      guest: false,
    });

    Object.defineProperty(window, 'location', {
      value: { pathname: '/beta-access/denied', search: '', replace: jest.fn(), href: '' },
      writable: true,
    });

  render(<App />);

    expect(screen.getByTestId('beta-access-denied')).toBeInTheDocument();
  });

  test('redirects to beta access request when user has no beta access status', async () => {
    const mockReplace = jest.fn();
    Object.defineProperty(window, 'location', {
      value: { pathname: '/', search: '', replace: mockReplace, href: '' },
      writable: true,
    });

    mockUseAuth.mockReturnValue({
      user: { authenticated: true, beta_access_status: undefined },
      loading: false,
      guest: false,
    });

  render(<App />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/beta-access/request');
    });
  });

  test('redirects to beta access request when user has not requested status', async () => {
    const mockReplace = jest.fn();
    Object.defineProperty(window, 'location', {
      value: { pathname: '/', search: '', replace: mockReplace, href: '' },
      writable: true,
    });

    mockUseAuth.mockReturnValue({
      user: { authenticated: true, beta_access_status: 'not_requested' },
      loading: false,
      guest: false,
    });

    render(<App />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/beta-access/request');
    });
  });

  test('redirects to beta access pending when user has pending status', async () => {
    const mockReplace = jest.fn();
    Object.defineProperty(window, 'location', {
      value: { pathname: '/', search: '', replace: mockReplace, href: '' },
      writable: true,
    });

    mockUseAuth.mockReturnValue({
      user: { authenticated: true, beta_access_status: 'pending' },
      loading: false,
      guest: false,
    });

  render(<App />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/beta-access/pending');
    });
  });

  test('redirects to beta access denied when user has denied status', async () => {
    const mockReplace = jest.fn();
    Object.defineProperty(window, 'location', {
      value: { pathname: '/', search: '', replace: mockReplace, href: '' },
      writable: true,
    });

    mockUseAuth.mockReturnValue({
      user: { authenticated: true, beta_access_status: 'denied' },
      loading: false,
      guest: false,
    });

  render(<App />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/beta-access/denied');
    });
  });

  test('redirects to dashboard when user has accepted status', async () => {
    const mockReplace = jest.fn();
    Object.defineProperty(window, 'location', {
      value: { pathname: '/', search: '', replace: mockReplace, href: '' },
      writable: true,
    });

    mockUseAuth.mockReturnValue({
      user: { authenticated: true, beta_access_status: 'accepted' },
      loading: false,
      guest: false,
    });

  render(<App />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/dashboard');
    });
  });

  test('prevents access to dashboard routes when user has pending beta access', () => {
    const mockReplace = jest.fn();
    Object.defineProperty(window, 'location', {
      value: { pathname: '/dashboard', search: '', replace: mockReplace, href: '' },
      writable: true,
    });

    mockUseAuth.mockReturnValue({
      user: { authenticated: true, beta_access_status: 'pending' },
      loading: false,
      guest: false,
    });

  render(<App />);

    expect(mockReplace).toHaveBeenCalledWith('/beta-access/pending');
  });

  test('prevents access to dashboard routes when user has denied beta access', () => {
    const mockReplace = jest.fn();
    Object.defineProperty(window, 'location', {
      value: { pathname: '/profile', search: '', replace: mockReplace, href: '' },
      writable: true,
    });

    mockUseAuth.mockReturnValue({
      user: { authenticated: true, beta_access_status: 'denied' },
      loading: false,
      guest: false,
    });

  render(<App />);

    expect(mockReplace).toHaveBeenCalledWith('/beta-access/denied');
  });

  test('prevents access to dashboard routes when user has no beta access', () => {
    const mockReplace = jest.fn();
    Object.defineProperty(window, 'location', {
      value: { pathname: '/memory-blocks', search: '', replace: mockReplace, href: '' },
      writable: true,
    });

    mockUseAuth.mockReturnValue({
      user: { authenticated: true, beta_access_status: undefined },
      loading: false,
      guest: false,
    });

  render(<App />);

    expect(mockReplace).toHaveBeenCalledWith('/beta-access/request');
  });

  test('allows access to dashboard routes when user has accepted beta access', () => {
    Object.defineProperty(window, 'location', {
      value: { pathname: '/dashboard', search: '', replace: jest.fn(), href: 'http://localhost/dashboard', origin: 'http://localhost' },
      writable: true,
    });

    mockUseAuth.mockReturnValue({
      user: { authenticated: true, beta_access_status: 'accepted' },
      loading: false,
      guest: false,
    });

  render(<App />);

    expect(screen.getByTestId('layout')).toBeInTheDocument();
    expect(screen.getByTestId('dashboard')).toBeInTheDocument();
  });

  test('processes beta review token acceptance and redirects to confirmation with email', async () => {
    const mockReplace = jest.fn();
    Object.defineProperty(window, 'location', {
      value: {
        pathname: '/login',
        search: '?beta_review=req-123&beta_decision=accepted&beta_token=tok-abc',
        replace: mockReplace,
        href: '',
        hash: '',
        origin: 'http://localhost',
      },
      writable: true,
    });

    betaAccessServiceMock.reviewWithToken.mockResolvedValue({
      success: true,
      message: 'Beta access approved for tester@example.com',
      request_email: 'tester@example.com',
      decision: 'accepted',
      already_processed: false,
    });

    mockUseAuth.mockReturnValue({
      user: { authenticated: true, beta_access_status: 'accepted' },
      loading: false,
      guest: false,
    });

    render(<App />);

    await waitFor(() => {
      expect(betaAccessServiceMock.reviewWithToken).toHaveBeenCalledWith('req-123', 'accepted', 'tok-abc');
    });

    expect(notifications.showSuccess).toHaveBeenCalledWith(expect.stringContaining('approved'));
    expect(mockReplace).toHaveBeenCalledWith('/beta-access/review/granted?email=tester%40example.com');
  });

  test('processes already handled review token and flags status as already', async () => {
    const mockReplace = jest.fn();
    Object.defineProperty(window, 'location', {
      value: {
        pathname: '/login',
        search: '?beta_review=req-456&beta_decision=ACCEPTED&beta_token=tok-def',
        replace: mockReplace,
        href: '',
        hash: '',
        origin: 'http://localhost',
      },
      writable: true,
    });

    betaAccessServiceMock.reviewWithToken.mockResolvedValue({
      success: true,
      message: 'Already processed',
      request_email: 'existing@example.com',
      decision: 'accepted',
      already_processed: true,
    });

    mockUseAuth.mockReturnValue({
      user: { authenticated: true, beta_access_status: 'accepted' },
      loading: false,
      guest: false,
    });

    render(<App />);

    await waitFor(() => {
      expect(betaAccessServiceMock.reviewWithToken).toHaveBeenCalledWith('req-456', 'accepted', 'tok-def');
    });

    expect(notifications.showSuccess).toHaveBeenCalled();
    expect(mockReplace).toHaveBeenCalledWith('/beta-access/review/granted?email=existing%40example.com&status=already');
  });
});
