import authService from '../authService';

describe('authService.getCurrentUser', () => {
  afterEach(() => {
    global.fetch && jest.restoreAllMocks();
  });

  test('returns JSON on success', async () => {
    const data = { authenticated: true, email: 'user@example.com' };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => data });
    const result = await authService.getCurrentUser();
    expect(result).toEqual(data);
  });

  test('returns {authenticated:false} on 401', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: false, status: 401 });
    const result = await authService.getCurrentUser();
    expect(result).toEqual({ authenticated: false });
  });

  test('returns {authenticated:false} on non-401 error code', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: false, status: 500 });
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
    jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(authService, 'getCurrentUser').mockRejectedValue(new Error('boom'));
    await expect(authService.isAuthenticated()).resolves.toBe(false);
    console.error.mockRestore();
  });
});
