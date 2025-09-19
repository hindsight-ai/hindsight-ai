import React from 'react';
import { UIMemoryBlock } from '../types/domain';

const formatFullDate = (value?: string): string => {
  if (!value) return 'Unknown';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unknown';
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const formatRelativeTime = (value?: string): string => {
  if (!value) return 'Unknown';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unknown';
  const diffMs = Date.now() - date.getTime();
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.round(days / 30);
  if (months < 12) return `${months}mo ago`;
  const years = Math.round(months / 12);
  return `${years}y ago`;
};

const truncate = (value?: string, maxLength = 220): string => {
  if (!value) return 'No content available.';
  const trimmed = value.trim();
  if (trimmed.length <= maxLength) return trimmed;
  return `${trimmed.slice(0, maxLength)}…`;
};

interface ArchivedMemoryCardProps {
  memoryBlock: UIMemoryBlock & { keywords?: string[]; archived_at?: string; agent_name?: string };
  agentName: string;
  onView: (id: string) => void;
  onRestore: (id: string) => Promise<void> | void;
  onDelete: (id: string) => Promise<void> | void;
  actionPending?: boolean;
}

const badgeClasses = 'inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium';

const ArchivedMemoryCard: React.FC<ArchivedMemoryCardProps> = ({ memoryBlock, agentName, onView, onRestore, onDelete, actionPending = false }) => {
  const keywords = Array.isArray(memoryBlock.keywords)
    ? memoryBlock.keywords
    : []; // ensure array

  const contentPreview = truncate(
    memoryBlock.lessons_learned || (memoryBlock as any).summary || memoryBlock.content
  );

  const conversationLabel = memoryBlock.conversation_id
    ? `Conversation ${memoryBlock.conversation_id.slice(-6)}`
    : null;

  return (
    <div
      className="group relative flex h-full cursor-pointer flex-col rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md"
      onClick={() => onView(memoryBlock.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onView(memoryBlock.id);
        }
      }}
    >
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-blue-600">
              Archived {memoryBlock.archived_at ? formatRelativeTime(memoryBlock.archived_at) : '—'}
            </p>
            <div className="text-lg font-semibold text-gray-900">
              {agentName}
            </div>
            <div className="flex flex-wrap gap-2 text-xs text-gray-500">
              {conversationLabel && (
                <span className={`${badgeClasses} border-blue-100 bg-blue-50 text-blue-600`}>
                  <svg className="h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 11c.5304 0 1.0391-.2107 1.4142-.5858C13.7893 10.0391 14 9.5304 14 9s-.2107-1.0391-.5858-1.4142C13.0391 7.2107 12.5304 7 12 7c-.5304 0-1.0391.2107-1.4142.5858C10.2107 7.9609 10 8.4696 10 9s.2107 1.0391.5858 1.4142C10.9609 10.7893 11.4696 11 12 11zm0 9c-2.3333-2.6667-7-4-7-7 0-3.3333 3-5 7-5s7 1.6667 7 5c0 3-4.6667 4.3333-7 7z" />
                  </svg>
                  {conversationLabel}
                </span>
              )}
              {memoryBlock.feedback_score != null && (
                <span
                  className={`${badgeClasses} ${
                    memoryBlock.feedback_score >= 80
                      ? 'border-green-100 bg-green-50 text-green-600'
                      : memoryBlock.feedback_score >= 60
                      ? 'border-yellow-100 bg-yellow-50 text-yellow-600'
                      : 'border-red-100 bg-red-50 text-red-600'
                  }`}
                >
                  Feedback {memoryBlock.feedback_score}
                </span>
              )}
              {memoryBlock.retrieval_count != null && (
                <span className={`${badgeClasses} border-purple-100 bg-purple-50 text-purple-600`}>
                  {memoryBlock.retrieval_count} retrievals
                </span>
              )}
            </div>
          </div>
          <div className="rounded-full bg-blue-50 p-3 text-blue-500">
            <svg className="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V7m-5 4l-3 3-3-3m3 3V4" />
            </svg>
          </div>
        </div>

        <p className="text-sm leading-relaxed text-gray-600">
          {contentPreview}
        </p>

        {keywords.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {keywords.slice(0, 6).map((keyword, index) => (
              <span
                key={index}
                className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600"
              >
                #{keyword}
              </span>
            ))}
            {keywords.length > 6 && (
              <span className="inline-flex items-center rounded-full bg-slate-50 px-2 py-1 text-xs text-slate-500">
                +{keywords.length - 6} more
              </span>
            )}
          </div>
        )}
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 pt-4 text-xs text-gray-500">
        <div>
          <span title={memoryBlock.archived_at ? formatFullDate(memoryBlock.archived_at) : undefined}>
            Archived {memoryBlock.archived_at ? formatFullDate(memoryBlock.archived_at) : 'Unavailable'}
          </span>
          {' · '}
          <span title={formatFullDate(memoryBlock.created_at)}>
            Created {formatFullDate(memoryBlock.created_at)}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onView(memoryBlock.id);
            }}
            className="inline-flex items-center rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:border-gray-300 hover:text-gray-800"
          >
            View details
          </button>
          <button
            type="button"
            onClick={async (event) => {
              event.stopPropagation();
              await onRestore(memoryBlock.id);
            }}
            disabled={actionPending}
            className="inline-flex items-center rounded-lg border border-green-200 bg-green-50 px-3 py-1.5 text-xs font-medium text-green-600 transition hover:border-green-300 hover:bg-green-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <svg className="mr-1 h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9" />
            </svg>
            Restore
          </button>
          <button
            type="button"
            onClick={async (event) => {
              event.stopPropagation();
              await onDelete(memoryBlock.id);
            }}
            disabled={actionPending}
            className="inline-flex items-center rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:border-red-300 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <svg className="mr-1 h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Delete
          </button>
        </div>
      </div>
    </div>
  );
};

export default ArchivedMemoryCard;
