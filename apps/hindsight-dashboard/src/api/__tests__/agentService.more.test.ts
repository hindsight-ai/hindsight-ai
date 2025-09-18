import agentService from '../agentService';

jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: { show401Error: jest.fn(), showWarning: jest.fn() },
}));

describe('agentService full coverage', () => {
  beforeEach(() => { global.fetch.mockReset && global.fetch.mockReset(); });

  test('getAgentById returns JSON', async () => {
    const resp = { agent_id: 'a1' };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const r = await agentService.getAgentById('a1');
    expect(r).toEqual(resp);
    expect(global.fetch.mock.calls[0][0]).toContain('/agents/a1');
  });

  test('updateAgent PUT', async () => {
    const resp = { agent_id: 'a1', agent_name: 'x' };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const r = await agentService.updateAgent('a1', { agent_name: 'x' });
    expect(r).toEqual(resp);
    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.method).toBe('PUT');
  });

  test('deleteAgent 204 returns undefined', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, status: 204 });
    const r = await agentService.deleteAgent('a1');
    expect(r).toBeUndefined();
    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.method).toBe('DELETE');
  });

  test('searchAgents builds query and uses base()', async () => {
    Object.defineProperty(window, 'sessionStorage', { value: { getItem: () => 'true' }, configurable: true });
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => ({ items: [] }) });
    await agentService.searchAgents('john');
    const [url] = global.fetch.mock.calls[0];
    expect(url).toContain('/guest-api/agents/search/');
    expect(url).toContain('query=john');
  });

  test('agentService upgrades http base to https under https app', async () => {
    Object.defineProperty(window, 'location', { value: new URL('https://app.example.com/'), writable: true });
    Object.defineProperty(window, 'sessionStorage', { value: { getItem: () => 'false' }, configurable: true });
    window.__ENV__ = { HINDSIGHT_SERVICE_API_URL: 'http://api.example.com' };
    jest.resetModules();
    const mod = (await import('../agentService')).default;
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [] }) });
    await mod.getAgents();
    const calledUrl = global.fetch.mock.calls[0][0];
    expect(calledUrl).toContain('https://api.example.com');
  });

  test('getAgents returns empty on JSON parse error', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
    Object.defineProperty(window, 'location', { value: new URL('http://localhost/'), writable: true });
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => { throw new Error('bad json'); } });
    const r = await agentService.getAgents();
    expect(r).toEqual({ items: [] });
    console.error.mockRestore();
  });

  test('getAgents returns {items: []} when API returns non-array object', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => ({ foo: 'bar' }) });
    const r = await agentService.getAgents();
    expect(r).toEqual({ items: [] });
  });

  test('deleteAgent returns JSON when 200', async () => {
    Object.defineProperty(window, 'sessionStorage', { value: { getItem: () => 'false' }, configurable: true });
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, status: 200, json: async () => ({ deleted: true }) });
    const res = await agentService.deleteAgent('a1');
    expect(res).toEqual({ deleted: true });
  });
});
