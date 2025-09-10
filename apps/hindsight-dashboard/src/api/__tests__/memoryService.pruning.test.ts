import memoryService from '../memoryService';

jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: { show401Error: jest.fn(), showWarning: jest.fn() },
}));

describe('memoryService pruning and compression', () => {
  beforeEach(() => { global.fetch.mockReset && global.fetch.mockReset(); });

  test('generatePruningSuggestions POSTs body params', async () => {
    const resp = { suggestions: [] };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.generatePruningSuggestions({ batch_size: 10 });
    expect(data).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory/prune/suggest');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({ batch_size: 10 });
  });

  test('confirmPruning POSTs ids', async () => {
    const resp = { success: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const ids = ['m1','m2'];
    const data = await memoryService.confirmPruning(ids);
    expect(data).toEqual(resp);
    const body = JSON.parse(global.fetch.mock.calls[0][1].body);
    expect(body.memory_block_ids).toEqual(ids);
  });

  test('suggestKeywords POST', async () => {
    const resp = { suggestions: ['k1'] };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.suggestKeywords('mb1');
    expect(data).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-blocks/mb1/suggest-keywords');
    expect(opts.method).toBe('POST');
  });

  test('compressMemoryBlock POSTs instructions', async () => {
    const resp = { compressed: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.compressMemoryBlock('mb1', { rules: 'x' });
    expect(data).toEqual(resp);
    const body = JSON.parse(global.fetch.mock.calls[0][1].body);
    expect(body).toEqual({ rules: 'x' });
  });

  test('applyMemoryCompression POSTs payload', async () => {
    const resp = { applied: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.applyMemoryCompression('mb1', { a: 1 });
    expect(data).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-blocks/mb1/compress/apply');
    expect(JSON.parse(opts.body)).toEqual({ a: 1 });
  });
});

