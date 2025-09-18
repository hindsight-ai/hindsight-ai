import React from 'react';
import { render, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ConsolidationSuggestions from '../ConsolidationSuggestions';

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

jest.mock('../../api/memoryService', () => ({
  __esModule: true,
  default: {
    getConsolidationSuggestions: jest.fn(async () => ({ items: [], total_items: 0, total_pages: 0 })),
  },
  getConsolidationSuggestions: jest.fn(async () => ({ items: [], total_items: 0, total_pages: 0 })),
}));

describe('ConsolidationSuggestions reacts to org scope changes', () => {
  test('dispatching orgScopeChanged triggers data refresh', async () => {
    const mod = await import('../../api/memoryService');
    const getConsolidationSuggestions = (mod.getConsolidationSuggestions || (mod.default as any).getConsolidationSuggestions) as jest.Mock;

    render(<MemoryRouter><ConsolidationSuggestions /></MemoryRouter>);

    expect(getConsolidationSuggestions).toHaveBeenCalled();
    getConsolidationSuggestions.mockClear();

    await act(async () => {
      sessionStorage.setItem('ACTIVE_SCOPE', 'personal');
      window.dispatchEvent(new Event('orgScopeChanged'));
    });

    expect(getConsolidationSuggestions).toHaveBeenCalledTimes(1);
  });
});
