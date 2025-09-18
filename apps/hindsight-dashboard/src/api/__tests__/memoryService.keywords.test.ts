import memoryService from '../memoryService';

jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: { show401Error: jest.fn(), showWarning: jest.fn() },
}));

describe('memoryService keyword endpoints', () => {
  beforeEach(() => { global.fetch.mockReset && global.fetch.mockReset(); });

  test('getKeywords returns list', async () => {
    const payload = [{ keyword_id: 'k1', keyword_text: 'foo' }];
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => payload });
    const data = await memoryService.getKeywords();
    expect(data).toEqual(payload);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/keywords/');
    expect(opts.credentials).toBe('include');
  });

  test('getKeywords 401 triggers notification', async () => {
    const notification = require('../../services/notificationService').default;
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: false, status: 401 });
    await expect(memoryService.getKeywords()).rejects.toThrow('Authentication required');
    expect(notification.show401Error).toHaveBeenCalled();
  });

  test('createKeyword POSTs JSON', async () => {
    const resp = { keyword_id: 'k1' };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.createKeyword({ keyword_text: 'bar' });
    expect(data).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/keywords/');
    expect(opts.method).toBe('POST');
    expect(opts.headers['Content-Type']).toBe('application/json');
  });

  test('updateKeyword PUTs JSON', async () => {
    const resp = { keyword_id: 'k1', keyword_text: 'baz' };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.updateKeyword('k1', { keyword_text: 'baz' });
    expect(data).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/keywords/k1');
    expect(opts.method).toBe('PUT');
    expect(opts.headers['Content-Type']).toBe('application/json');
  });

  test('deleteKeyword DELETEs and returns JSON', async () => {
    const resp = { ok: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.deleteKeyword('k1');
    expect(data).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/keywords/k1');
    expect(opts.method).toBe('DELETE');
  });

  test('getKeywordMemoryBlocks builds skip/limit', async () => {
    const resp = { items: [] };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    await memoryService.getKeywordMemoryBlocks('k1', 20, 5);
    const [url] = global.fetch.mock.calls[0];
    expect(url).toContain('/keywords/k1/memory-blocks/?');
    expect(url).toContain('skip=20');
    expect(url).toContain('limit=5');
  });

  test('getKeywordMemoryBlocksCount returns JSON', async () => {
    const resp = { count: 3 };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.getKeywordMemoryBlocksCount('k1');
    expect(data).toEqual(resp);
    const [url] = global.fetch.mock.calls[0];
    expect(url).toContain('/keywords/k1/memory-blocks/count');
  });

  test('addKeywordToMemoryBlock POSTs', async () => {
    const resp = { success: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.addKeywordToMemoryBlock('mb1', 'k1');
    expect(data).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-blocks/mb1/keywords/k1');
    expect(opts.method).toBe('POST');
  });

  test('removeKeywordFromMemoryBlock DELETEs', async () => {
    const resp = { success: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.removeKeywordFromMemoryBlock('mb1', 'k1');
    expect(data).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-blocks/mb1/keywords/k1');
    expect(opts.method).toBe('DELETE');
  });
});

