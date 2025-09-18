import memoryService from '../memoryService';

jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: { show401Error: jest.fn(), showWarning: jest.fn() },
}));

describe('memoryService optimization and bulk endpoints', () => {
  beforeEach(() => { global.fetch.mockReset && global.fetch.mockReset(); });

  test('getMemoryOptimizationSuggestions builds params', async () => {
    const payload = { items: [], total_items: 0 };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => payload });
    const filters = { agentId: 'a1', priority: 'high', dateRange: 'last_7_days' };
    const data = await memoryService.getMemoryOptimizationSuggestions(filters);
    expect(data).toEqual(payload);
    const [url] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-optimization/suggestions');
    expect(url).toContain('agent_id=a1');
    expect(url).toContain('priority=high');
    expect(url).toContain('date_range=last_7_days');
  });

  test('executeOptimizationSuggestion POSTs', async () => {
    const resp = { success: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.executeOptimizationSuggestion('s1');
    expect(data).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-optimization/suggestions/s1/execute');
    expect(opts.method).toBe('POST');
  });

  test('getSuggestionDetails returns JSON', async () => {
    const resp = { suggestion_id: 's1' };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.getSuggestionDetails('s1');
    expect(data).toEqual(resp);
    const [url] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-optimization/suggestions/s1');
  });

  test('bulkCompactMemoryBlocks POSTs correct body', async () => {
    const resp = { success: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const ids = ['m1', 'm2'];
    await memoryService.bulkCompactMemoryBlocks(ids, 'instr', 3);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-blocks/bulk-compact');
    expect(opts.method).toBe('POST');
    const body = JSON.parse(opts.body);
    expect(body.memory_block_ids).toEqual(ids);
    expect(body.user_instructions).toBe('instr');
    expect(body.max_concurrent).toBe(3);
  });

  test('bulkGenerateKeywords POSTs ids', async () => {
    const resp = { suggestions: [], successful_count: 2, total_processed: 2 };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const ids = ['m1', 'm2'];
    const res = await memoryService.bulkGenerateKeywords(ids);
    expect(res).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-blocks/bulk-generate-keywords');
    const body = JSON.parse(opts.body);
    expect(body.memory_block_ids).toEqual(ids);
  });

  test('bulkApplyKeywords POSTs applications', async () => {
    const resp = { results: [], successful_count: 1, total_processed: 1 };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const apps = [{ memory_block_id: 'm1', keywords: ['x'] }];
    const res = await memoryService.bulkApplyKeywords(apps);
    expect(res).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-blocks/bulk-apply-keywords');
    const body = JSON.parse(opts.body);
    expect(body.applications).toEqual(apps);
  });

  test('mergeMemoryBlocks POSTs ids and content', async () => {
    const resp = { merged: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const ids = ['m1', 'm2'];
    const res = await memoryService.mergeMemoryBlocks(ids, 'merged-content');
    expect(res).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-blocks/merge');
    const body = JSON.parse(opts.body);
    expect(body.memory_block_ids).toEqual(ids);
    expect(body.merged_content).toBe('merged-content');
  });
});

describe('memoryService batched helpers', () => {
  test('bulkGenerateKeywordsBatched aggregates batches and progress', async () => {
    const ids = Array.from({ length: 5 }, (_, i) => `m${i+1}`);
    const onProgress = jest.fn();
    jest.spyOn(memoryService, 'bulkGenerateKeywords').mockResolvedValueOnce({ suggestions: ['a'], successful_count: 2, failed_count: 0, total_processed: 2 })
      .mockResolvedValueOnce({ suggestions: ['b','c'], successful_count: 3, failed_count: 0, total_processed: 3 });
    const res = await memoryService.bulkGenerateKeywordsBatched(ids, { batchSize: 2, onProgress });
    expect(res.successful_count).toBe(5);
    expect(res.suggestions).toEqual(['a','b','c']);
    expect(onProgress).toHaveBeenCalledTimes(3); // after each batch
  });

  test('bulkApplyKeywordsBatched aggregates results and progress', async () => {
    const apps = Array.from({ length: 4 }, (_, i) => ({ memory_block_id: `m${i+1}`, keywords: ['x'] }));
    const onProgress = jest.fn();
    jest.spyOn(memoryService, 'bulkApplyKeywords').mockResolvedValueOnce({ results: ['r1'], successful_count: 2, failed_count: 0 })
      .mockResolvedValueOnce({ results: ['r2','r3'], successful_count: 2, failed_count: 0 });
    const res = await memoryService.bulkApplyKeywordsBatched(apps, { batchSize: 2, onProgress });
    expect(res.successful_count).toBe(4);
    expect(res.results).toEqual(['r1','r2','r3']);
    expect(onProgress).toHaveBeenCalledTimes(2);
  });
});

