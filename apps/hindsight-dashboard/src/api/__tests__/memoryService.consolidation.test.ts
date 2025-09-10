import memoryService from '../memoryService';

jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: { show401Error: jest.fn(), showWarning: jest.fn() },
}));

describe('memoryService consolidation endpoints', () => {
  beforeEach(() => { global.fetch.mockReset && global.fetch.mockReset(); });

  test('getConsolidationSuggestions builds filter params', async () => {
    const payload = { items: [], total_items: 0 };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => payload });
    const filters = { skip: 5, limit: 10, status: 'pending', group_id: 'g1', sort_by: 'created_at', sort_order: 'desc' };
    const data = await memoryService.getConsolidationSuggestions(filters);
    expect(data).toEqual(payload);
    const [url] = global.fetch.mock.calls[0];
    expect(url).toContain('/consolidation-suggestions/?');
    expect(url).toContain('skip=5');
    expect(url).toContain('limit=10');
    expect(url).toContain('status=pending');
    expect(url).toContain('group_id=g1');
    expect(url).toContain('sort_by=created_at');
    expect(url).toContain('sort_order=desc');
  });

  test('getConsolidationSuggestionById returns JSON', async () => {
    const resp = { suggestion_id: 's1' };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.getConsolidationSuggestionById('s1');
    expect(data).toEqual(resp);
    const [url] = global.fetch.mock.calls[0];
    expect(url).toContain('/consolidation-suggestions/s1');
  });

  test('validateConsolidationSuggestion POSTs and returns JSON', async () => {
    const resp = { success: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.validateConsolidationSuggestion('s1');
    expect(data).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/consolidation-suggestions/s1/validate/');
    expect(opts.method).toBe('POST');
    expect(opts.headers['Content-Type']).toBe('application/json');
  });

  test('rejectConsolidationSuggestion POSTs and returns JSON', async () => {
    const resp = { success: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.rejectConsolidationSuggestion('s1');
    expect(data).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/consolidation-suggestions/s1/reject/');
    expect(opts.method).toBe('POST');
    expect(opts.headers['Content-Type']).toBe('application/json');
  });
});

