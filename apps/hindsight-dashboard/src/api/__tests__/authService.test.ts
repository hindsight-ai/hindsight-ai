import authService from '../authService';

describe('authService.getCurrentUser', () => {
  afterEach(() => {
    global.fetch && jest.restoreAllMocks();
  });

  test('returns JSON with beta_access_status on success', async () => {
    const data = {
      authenticated: true,
      email: 'user@example.com',
      beta_access_status: 'pending' as const
    };
    const mockResponse = { ok: true, json: jest.fn().mockResolvedValue(data) };
    jest.spyOn(global, 'fetch').mockResolvedValue(mockResponse as any);
    const result = await authService.getCurrentUser();
    expect(result).toEqual(data);
    expect(result.beta_access_status).toBe('pending');
  });

  test('returns JSON with accepted beta_access_status', async () => {
    const data = {
      authenticated: true,
      email: 'user@example.com',
      beta_access_status: 'accepted' as const
    };
    const mockResponse = { ok: true, json: jest.fn().mockResolvedValue(data) };
    jest.spyOn(global, 'fetch').mockResolvedValue(mockResponse as any);
    const result = await authService.getCurrentUser();
    expect(result).toEqual(data);
    expect(result.beta_access_status).toBe('accepted');
  });

  test('returns JSON with denied beta_access_status', async () => {
    const data = {
      authenticated: true,
      email: 'user@example.com',
      beta_access_status: 'denied' as const
    };
    const mockResponse = { ok: true, json: jest.fn().mockResolvedValue(data) };
    jest.spyOn(global, 'fetch').mockResolvedValue(mockResponse as any);
    const result = await authService.getCurrentUser();
    expect(result).toEqual(data);
    expect(result.beta_access_status).toBe('denied');
  });

  test('returns JSON with not_requested beta_access_status', async () => {
    const data = {
      authenticated: true,
      email: 'user@example.com',
      beta_access_status: 'not_requested' as const
    };
    const mockResponse = { ok: true, json: jest.fn().mockResolvedValue(data) };
    jest.spyOn(global, 'fetch').mockResolvedValue(mockResponse as any);
    const result = await authService.getCurrentUser();
    expect(result).toEqual(data);
    expect(result.beta_access_status).toBe('not_requested');
  });

  test('returns JSON with undefined beta_access_status', async () => {
    const data = {
      authenticated: true,
      email: 'user@example.com',
      beta_access_status: undefined
    };
    const mockResponse = { ok: true, json: jest.fn().mockResolvedValue(data) };
    jest.spyOn(global, 'fetch').mockResolvedValue(mockResponse as any);
    const result = await authService.getCurrentUser();
    expect(result).toEqual(data);
    expect(result.beta_access_status).toBeUndefined();
  });

  test('returns {authenticated:false} on 401', async () => {
    const mockResponse = { ok: false, status: 401 };
    jest.spyOn(global, 'fetch').mockResolvedValue(mockResponse as any);
    const result = await authService.getCurrentUser();
    expect(result).toEqual({ authenticated: false });
  });

  test('returns {authenticated:false} on non-401 error code', async () => {
    const mockResponse = { ok: false, status: 500 };
    jest.spyOn(global, 'fetch').mockResolvedValue(mockResponse as any);
    const result = await authService.getCurrentUser();
    expect(result).toEqual({ authenticated: false });
  });

  test('returns {authenticated:false} on network error', async () => {
    jest.spyOn(global, 'fetch').mockRejectedValue(new Error('network'));
    const result = await authService.getCurrentUser();
    expect(result).toEqual({ authenticated: false });
  });
});

describe('authService.isAuthenticated', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('returns true when current user is authenticated', async () => {
    jest.spyOn(authService, 'getCurrentUser').mockResolvedValue({ authenticated: true });
    await expect(authService.isAuthenticated()).resolves.toBe(true);
  });

  test('returns false when current user is unauthenticated', async () => {
    jest.spyOn(authService, 'getCurrentUser').mockResolvedValue({ authenticated: false });
    await expect(authService.isAuthenticated()).resolves.toBe(false);
  });

  test('isAuthenticated returns false when getCurrentUser throws', async () => {
    const mockConsoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(authService, 'getCurrentUser').mockRejectedValue(new Error('boom'));
    await expect(authService.isAuthenticated()).resolves.toBe(false);
    mockConsoleError.mockRestore();
  });
});
