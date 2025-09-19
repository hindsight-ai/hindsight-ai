import React from 'react';
import { render, screen } from '@testing-library/react';
import ArchivedMemoryCard from '../ArchivedMemoryCard';

const baseMemoryBlock = {
  id: 'memory-1',
  archived_at: '2024-01-02T00:00:00.000Z',
  created_at: '2024-01-01T00:00:00.000Z',
  conversation_id: '11111111-2222-3333-4444-555555555555',
  lessons_learned: 'Capturing a concise summary of the archived memory.',
  feedback_score: 72,
  retrieval_count: 5,
};

describe('ArchivedMemoryCard', () => {
  it('normalizes keyword objects into displayable chips without crashing', () => {
    const onView = jest.fn();
    const onRestore = jest.fn();
    const onDelete = jest.fn();

    render(
      <ArchivedMemoryCard
        memoryBlock={{
          ...baseMemoryBlock,
          keywords: [
            { keyword_text: 'Memory' },
            { keyword: 'AI' },
            { keyword_text: 'Memory' },
            { name: 'Insights' },
            ' custom ',
          ] as any,
        }}
        agentName="Cline"
        onView={onView}
        onRestore={onRestore}
        onDelete={onDelete}
      />
    );

    expect(screen.getByText('#Memory')).toBeInTheDocument();
    expect(screen.getByText('#AI')).toBeInTheDocument();
    expect(screen.getByText('#Insights')).toBeInTheDocument();
    expect(screen.getByText('#custom')).toBeInTheDocument();

    const keywordChips = screen.getAllByText(/^#/);
    expect(keywordChips).toHaveLength(4);
  });
});
