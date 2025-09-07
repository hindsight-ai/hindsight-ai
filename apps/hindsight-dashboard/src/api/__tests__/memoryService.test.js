import memoryService from '../memoryService';

// Mock notificationService to verify 401 handling
jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: { show401Error: jest.fn(), showWarning: jest.fn() },
}));

describe('memoryService.getMemoryBlocks', () => {
  beforeEach(() => { global.fetch.mockReset && global.fetch.mockReset(); });
  afterEach(() => { jest.restoreAllMocks(); });

  test('maps per_page to limit and defaults include_archived=false', async () => {
    const json = { items: [], total_items: 0 };
    const fetchSpy = jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => json });
    await memoryService.getMemoryBlocks({ per_page: 25, skip: 10, agent_id: 'a1' });
    expect(fetchSpy).toHaveBeenCalled();
    const url = fetchSpy.mock.calls[0][0];
    expect(url).toContain('/memory-blocks/?');
    expect(url).toContain('limit=25');
    expect(url).toContain('include_archived=false');
    expect(url).toContain('skip=10');
    expect(url).toContain('agent_id=a1');
  });

  test('triggers 401 notification and throws on 401', async () => {
    const notification = require('../../services/notificationService').default;
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: false, status: 401 });
    await expect(memoryService.getMemoryBlocks()).rejects.toThrow('Authentication required');
    expect(notification.show401Error).toHaveBeenCalled();
  });
});

describe('memoryService.updateMemoryBlock', () => {
  beforeEach(() => { global.fetch.mockReset && global.fetch.mockReset(); });
  afterEach(() => jest.restoreAllMocks());

  test('PUTs to API and returns JSON', async () => {
    const responseJson = { id: 'mb1', content: 'x' };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => responseJson });
    const r = await memoryService.updateMemoryBlock('mb1', { content: 'x' });
    expect(r).toEqual(responseJson);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-blocks/mb1');
    expect(opts.method).toBe('PUT');
    expect(opts.headers['Content-Type']).toBe('application/json');
  });
});
