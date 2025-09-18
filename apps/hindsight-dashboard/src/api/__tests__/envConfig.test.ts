describe('API base URL config and https upgrade', () => {
  const originalEnv = process.env;
  let originalLocation;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
    originalLocation = window.location;
  });

  afterEach(() => {
    process.env = originalEnv;
    Object.defineProperty(window, 'location', { value: originalLocation, writable: true });
    delete window.__ENV__;
  });

  test('memoryService upgrades http -> https when app runs on https', async () => {
    // Set window to https and runtime env to http
    Object.defineProperty(window, 'location', { value: new URL('https://app.example.com/'), writable: true });
    window.__ENV__ = { HINDSIGHT_SERVICE_API_URL: 'http://api.example.com' };

    jest.resetModules();
    const mod = await import('../memoryService');

    // Trigger a GET to confirm that upgraded URL was used
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    await mod.getBuildInfo();
    const calledUrl = global.fetch.mock.calls[0][0];
    expect(calledUrl.startsWith('https://')).toBe(true);
  });

  test('agentService falls back to process.env when window.__ENV__ missing', async () => {
    Object.defineProperty(window, 'location', { value: new URL('http://localhost/'), writable: true });
    delete window.__ENV__;
    process.env.VITE_HINDSIGHT_SERVICE_API_URL = 'https://env-api.example.com';

    jest.resetModules();
    const mod = await import('../agentService');
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [] }) });
    await mod.default.getAgents();
    const calledUrl = global.fetch.mock.calls[0][0];
    expect(calledUrl).toContain('https://env-api.example.com');
  });

  test('memoryService uses process.env fallback when window.__ENV__ missing', async () => {
    Object.defineProperty(window, 'location', { value: new URL('http://localhost/'), writable: true });
    delete window.__ENV__;
    process.env.VITE_HINDSIGHT_SERVICE_API_URL = 'https://env-api2.example.com';
    jest.resetModules();
    const mod = await import('../memoryService');
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    await mod.getBuildInfo();
    const calledUrl = global.fetch.mock.calls[0][0];
    expect(calledUrl).toContain('https://env-api2.example.com');
  });

  test('memoryService handles invalid URL gracefully (catch branch)', async () => {
    Object.defineProperty(window, 'location', { value: new URL('https://app.example.com/'), writable: true });
    window.__ENV__ = { HINDSIGHT_SERVICE_API_URL: ':::::' };

    jest.resetModules();
    await expect(import('../memoryService')).resolves.toBeDefined();
  });
});
