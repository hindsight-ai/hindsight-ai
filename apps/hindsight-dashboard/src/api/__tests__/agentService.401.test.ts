import agentService from '../agentService';

jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: { show401Error: jest.fn(), showWarning: jest.fn() },
}));

describe('agentService 401 branches', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 401 });
    Object.defineProperty(window, 'sessionStorage', { value: { getItem: () => 'false' }, configurable: true });
  });

  const expectAuthRequired = async (fn) => {
    await expect(fn()).rejects.toThrow('Authentication required');
  };

  test('401 triggers auth error on endpoints', async () => {
    await expectAuthRequired(() => agentService.getAgents({}));
    await expectAuthRequired(() => agentService.getAgentById('a1'));
    await expectAuthRequired(() => agentService.createAgent({ agent_name: 'x' }));
    await expectAuthRequired(() => agentService.deleteAgent('a1'));
    await expectAuthRequired(() => agentService.updateAgent('a1', { agent_name: 'y' }));
    await expectAuthRequired(() => agentService.searchAgents('john'));
  });
});

