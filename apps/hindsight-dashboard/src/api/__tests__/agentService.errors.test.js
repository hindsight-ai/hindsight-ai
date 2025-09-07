import agentService from '../agentService';

describe('agentService non-401 error branches', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 });
    // Ensure not in guest mode to hit fetch paths
    Object.defineProperty(window, 'sessionStorage', { value: { getItem: () => 'false' }, configurable: true });
  });

  const expectReject = async (fn) => {
    await expect(fn()).rejects.toThrow('HTTP error');
  };

  test('errors on various endpoints', async () => {
    await expectReject(() => agentService.getAgents({}));
    await expectReject(() => agentService.getAgentById('a1'));
    await expectReject(() => agentService.createAgent({ agent_name: 'x' }));
    await expectReject(() => agentService.deleteAgent('a1'));
    await expectReject(() => agentService.updateAgent('a1', { agent_name: 'y' }));
    await expectReject(() => agentService.searchAgents('john'));
  });
});

