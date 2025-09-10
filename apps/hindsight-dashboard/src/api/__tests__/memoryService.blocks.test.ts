import memoryService from '../memoryService';

jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: { show401Error: jest.fn(), showWarning: jest.fn() },
}));

describe('memoryService memory block endpoints', () => {
  beforeEach(() => { global.fetch.mockReset && global.fetch.mockReset(); });

  test('getMemoryBlockById returns JSON', async () => {
    const resp = { id: 'mb1', content: 'x' };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.getMemoryBlockById('mb1');
    expect(data).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-blocks/mb1');
    expect(opts.credentials).toBe('include');
  });

  test('archiveMemoryBlock posts and returns JSON', async () => {
    const resp = { status: 'archived' };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    const data = await memoryService.archiveMemoryBlock('mb1');
    expect(data).toEqual(resp);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-blocks/mb1/archive');
    expect(opts.method).toBe('POST');
  });

  test('deleteMemoryBlock returns undefined on 204', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, status: 204 });
    const data = await memoryService.deleteMemoryBlock('mb1');
    expect(data).toBeUndefined();
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-blocks/mb1/hard-delete');
    expect(opts.method).toBe('DELETE');
  });

  test('deleteMemoryBlock returns JSON on 200', async () => {
    const resp = { deleted: true };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, status: 200, json: async () => resp });
    const data = await memoryService.deleteMemoryBlock('mb1');
    expect(data).toEqual(resp);
  });

  test('getArchivedMemoryBlocks maps per_page to limit', async () => {
    const resp = { items: [], total_items: 0 };
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => resp });
    await memoryService.getArchivedMemoryBlocks({ per_page: 15, skip: 5 });
    const [url] = global.fetch.mock.calls[0];
    expect(url).toContain('/memory-blocks/archived/?');
    expect(url).toContain('limit=15');
    expect(url).toContain('skip=5');
  });

  test('deleteMemoryBlock 401 triggers notification', async () => {
    const notification = require('../../services/notificationService').default;
    jest.spyOn(global, 'fetch').mockResolvedValue({ ok: false, status: 401 });
    await expect(memoryService.deleteMemoryBlock('mb1')).rejects.toThrow('Authentication required');
    expect(notification.show401Error).toHaveBeenCalled();
  });
});
