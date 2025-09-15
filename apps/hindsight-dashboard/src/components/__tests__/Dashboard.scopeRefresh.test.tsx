import React from 'react';
import { render, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '../Dashboard';

jest.mock('../../api/agentService', () => ({
  __esModule: true,
  default: {
    getAgents: jest.fn(async () => ({ items: [] })),
  },
}));

jest.mock('../../api/memoryService', () => ({
  __esModule: true,
  default: {
    getMemoryBlocks: jest.fn(async () => ({ items: [], total_items: 0 })),
    getConversationsCount: jest.fn(async () => ({ count: 0 })),
  },
}));

describe('Dashboard reacts to org scope changes', () => {
  test('dispatching orgScopeChanged triggers data refresh', async () => {
    const agentService = (await import('../../api/agentService')).default as any;
    const memoryService = (await import('../../api/memoryService')).default as any;

    render(<MemoryRouter><Dashboard /></MemoryRouter>);

    // initial fetch
    expect(agentService.getAgents).toHaveBeenCalled();
    expect(memoryService.getMemoryBlocks).toHaveBeenCalled();
    expect(memoryService.getConversationsCount).toHaveBeenCalled();

    (agentService.getAgents as jest.Mock).mockClear();
    (memoryService.getMemoryBlocks as jest.Mock).mockClear();
    (memoryService.getConversationsCount as jest.Mock).mockClear();

    await act(async () => {
      // change scope and announce globally
      sessionStorage.setItem('ACTIVE_SCOPE', 'public');
      window.dispatchEvent(new Event('orgScopeChanged'));
    });

    expect(agentService.getAgents).toHaveBeenCalledTimes(1);
    // Dashboard calls getMemoryBlocks twice per fetch (recent + stats)
    expect(memoryService.getMemoryBlocks).toHaveBeenCalledTimes(2);
    expect(memoryService.getConversationsCount).toHaveBeenCalledTimes(1);
  });
});
