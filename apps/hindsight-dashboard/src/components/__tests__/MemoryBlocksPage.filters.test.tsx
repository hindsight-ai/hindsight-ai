import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MemoryBlocksPage from '../MemoryBlocksPage';

const mockGetAgents = jest.fn();
const mockGetMemoryBlocks = jest.fn();

jest.mock('../../context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    loading: false,
    guest: false,
    enterGuestMode: jest.fn(),
    exitGuestMode: jest.fn(),
    refresh: jest.fn(),
    features: {
      llmEnabled: true,
      consolidationEnabled: true,
      pruningEnabled: true,
      archivedEnabled: true,
    },
  }),
}));

jest.mock('../../api/agentService', () => ({
  __esModule: true,
  default: {
    getAgents: (...args: unknown[]) => mockGetAgents(...args),
  },
}));

jest.mock('../../api/memoryService', () => ({
  __esModule: true,
  default: {
    getMemoryBlocks: (...args: unknown[]) => mockGetMemoryBlocks(...args),
  },
}));

const flushTimersAndPromises = async () => {
  await act(async () => {
    jest.runOnlyPendingTimers();
  });
  await act(async () => {
    await Promise.resolve();
  });
};

describe('MemoryBlocksPage conversation filter validation', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockGetAgents.mockResolvedValue({ items: [] });
    mockGetMemoryBlocks.mockResolvedValue({ items: [], total_items: 0, total_pages: 0 });
  });

  afterEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  it('skips API calls when conversation ID is invalid and resumes when valid', async () => {
    render(
      <MemoryRouter>
        <MemoryBlocksPage />
      </MemoryRouter>
    );

    await flushTimersAndPromises();
    mockGetMemoryBlocks.mockClear();

    const conversationInput = screen.getByLabelText(/conversation id/i);

    await act(async () => {
      fireEvent.change(conversationInput, { target: { value: 'abc' } });
    });

    await act(async () => {
      jest.advanceTimersByTime(500);
    });
    await flushTimersAndPromises();

    expect(mockGetMemoryBlocks).not.toHaveBeenCalled();
    expect(screen.getByText(/enter a valid conversation id/i)).toBeInTheDocument();

    const validUuid = '00000000-0000-0000-0000-000000000000';
    await act(async () => {
      fireEvent.change(conversationInput, { target: { value: validUuid } });
    });

    await act(async () => {
      jest.advanceTimersByTime(500);
    });
    await flushTimersAndPromises();

    expect(mockGetMemoryBlocks).toHaveBeenCalledTimes(1);
    expect(mockGetMemoryBlocks.mock.calls[0][0]).toMatchObject({
      conversation_id: validUuid,
    });
  });
});
