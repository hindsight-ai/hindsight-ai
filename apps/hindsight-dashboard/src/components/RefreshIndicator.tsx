import React from 'react';
import LastUpdatedLabel from './LastUpdatedLabel';

interface RefreshIndicatorProps {
  lastUpdated?: Date | null;
  onRefresh: () => void;
  loading?: boolean;
  className?: string;
  buttonClassName?: string;
}

const RefreshIndicator: React.FC<RefreshIndicatorProps> = ({
  lastUpdated,
  onRefresh,
  loading = false,
  className = '',
  buttonClassName = ''
}) => {
  return (
    <div className={`flex items-center gap-2 text-sm text-gray-500 ${className}`}>
      <LastUpdatedLabel lastUpdated={lastUpdated} />
      <button
        type="button"
        onClick={onRefresh}
        disabled={loading}
        aria-label="Refresh data"
        title="Refresh data"
        className={`p-2 rounded-full text-gray-500 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-60 disabled:cursor-not-allowed ${buttonClassName}`}
      >
        <svg
          className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
      </button>
    </div>
  );
};

export default RefreshIndicator;
