import React from 'react';
import { render, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MemoryBlocksPage from '../MemoryBlocksPage';

jest.mock('../../api/agentService', () => ({
  __esModule: true,
  default: {
    getAgents: jest.fn(async () => ({ items: [] })),
  },
}));

jest.mock('../../api/memoryService', () => ({
  __esModule: true,
  default: {
    getMemoryBlocks: jest.fn(async () => ({ items: [], total_items: 0, total_pages: 0 })),
  },
}));

describe('MemoryBlocksPage reacts to org scope changes', () => {
  test('dispatching orgScopeChanged triggers data refresh', async () => {
    const agentService = (await import('../../api/agentService')).default as any;
    const memoryService = (await import('../../api/memoryService')).default as any;

    render(<MemoryRouter><MemoryBlocksPage /></MemoryRouter>);

    // initial fetches
    expect(agentService.getAgents).toHaveBeenCalled();
    expect(memoryService.getMemoryBlocks).toHaveBeenCalled();

    (agentService.getAgents as jest.Mock).mockClear();
    (memoryService.getMemoryBlocks as jest.Mock).mockClear();

    await act(async () => {
      sessionStorage.setItem('ACTIVE_SCOPE', 'organization');
      window.dispatchEvent(new Event('orgScopeChanged'));
    });

    expect(agentService.getAgents).toHaveBeenCalledTimes(1);
    expect(memoryService.getMemoryBlocks).toHaveBeenCalledTimes(1);
  });
});

