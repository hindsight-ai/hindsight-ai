import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ArchivedMemoryBlockList from '../ArchivedMemoryBlockList';

const mockGetAgents = jest.fn();
const mockGetArchivedMemoryBlocks = jest.fn();

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
    getArchivedMemoryBlocks: (...args: unknown[]) => mockGetArchivedMemoryBlocks(...args),
  },
}));

const flushPromises = async () => {
  await act(async () => {
    await Promise.resolve();
  });
};

describe('ArchivedMemoryBlockList conversation filter validation', () => {
  beforeEach(() => {
    mockGetAgents.mockResolvedValue({ items: [] });
    mockGetArchivedMemoryBlocks.mockResolvedValue({ items: [], total_items: 0, total_pages: 0 });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('prevents invalid conversation IDs from triggering API calls', async () => {
    render(
      <MemoryRouter>
        <ArchivedMemoryBlockList />
      </MemoryRouter>
    );

    await flushPromises();
    mockGetArchivedMemoryBlocks.mockClear();

    const conversationInput = screen.getByPlaceholderText(/filter by conversation/i);

    await act(async () => {
      fireEvent.change(conversationInput, { target: { value: 'xyz' } });
    });
    await flushPromises();

    expect(mockGetArchivedMemoryBlocks).not.toHaveBeenCalled();
    expect(screen.getByText(/enter a valid conversation id/i)).toBeInTheDocument();

    const validUuid = '00000000-0000-0000-0000-000000000000';
    await act(async () => {
      fireEvent.change(conversationInput, { target: { value: validUuid } });
    });
    await flushPromises();

    expect(mockGetArchivedMemoryBlocks).toHaveBeenCalledTimes(1);
    expect(mockGetArchivedMemoryBlocks.mock.calls[0][0]).toMatchObject({
      conversation_id: validUuid,
    });
  });
});
