import agentService from '../agentService';

jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: { show401Error: jest.fn(), showWarning: jest.fn() },
}));

describe('agentService.getAgents', () => {
  beforeEach(() => { global.fetch.mockReset && global.fetch.mockReset(); });

  test('maps per_page to limit and wraps raw array', async () => {
    const payload = [{ agent_id: 'a1' }];
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => payload });
    const result = await agentService.getAgents({ per_page: 10, q: 'x' });
    expect(Array.isArray(result.items)).toBe(true);
    expect(result.items).toHaveLength(1);
    const url = global.fetch.mock.calls[0][0];
    expect(url).toContain('/agents/?');
    expect(url).toContain('limit=10');
    expect(url).toContain('q=x');
  });

  test('401 triggers notification and throws', async () => {
    const notification = require('../../services/notificationService').default;
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: false, status: 401 });
    await expect(agentService.getAgents()).rejects.toThrow('Authentication required');
    expect(notification.show401Error).toHaveBeenCalled();
  });
});

describe('agentService.createAgent', () => {
  beforeEach(() => { global.fetch.mockReset && global.fetch.mockReset(); });

  test('POSTs to API and returns JSON', async () => {
    const resp = { agent_id: 'a1', agent_name: 'X' };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const result = await agentService.createAgent({ agent_name: 'X' });
    expect(result).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/agents/');
    expect(opts.method).toBe('POST');
    expect(opts.headers['Content-Type']).toBe('application/json');
  });
});

