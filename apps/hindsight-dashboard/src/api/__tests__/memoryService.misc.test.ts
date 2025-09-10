import memoryService from '../memoryService';

jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: { show401Error: jest.fn(), showWarning: jest.fn() },
}));

describe('memoryService misc endpoints', () => {
  beforeEach(() => { global.fetch.mockReset && global.fetch.mockReset(); });

  test('triggerConsolidation POSTs', async () => {
    const resp = { triggered: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const res = await memoryService.triggerConsolidation();
    expect(res).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/consolidation/trigger/');
    expect(opts.method).toBe('POST');
  });

  test('deleteConsolidationSuggestion returns undefined on 204', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, status: 204 });
    const res = await memoryService.deleteConsolidationSuggestion('s1');
    expect(res).toBeUndefined();
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/consolidation-suggestions/s1');
    expect(opts.method).toBe('DELETE');
  });

  test('deleteConsolidationSuggestion returns JSON on 200', async () => {
    const resp = { ok: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, status: 200, json: async () => resp });
    const res = await memoryService.deleteConsolidationSuggestion('s1');
    expect(res).toEqual(resp);
  });

  test('getBuildInfo returns JSON', async () => {
    const payload = { version: '1.0.0' };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => payload });
    const data = await memoryService.getBuildInfo();
    expect(data).toEqual(payload);
    const [url] = global.fetch.mock.calls[0];
    expect(url).toContain('/build-info');
  });

  test('getConversationsCount returns JSON', async () => {
    const payload = { count: 42 };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => payload });
    const data = await memoryService.getConversationsCount();
    expect(data).toEqual(payload);
    const [url] = global.fetch.mock.calls[0];
    expect(url).toContain('/conversations/count');
  });
});
