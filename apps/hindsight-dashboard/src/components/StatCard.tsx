import React from 'react';

interface StatCardProps {
  title: string;
  value: number | string;
  icon?: React.ReactNode;
  color?: 'blue' | 'purple' | 'green';
  loading?: boolean;
  error?: boolean;
  onClick?: () => void;
  compact?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color = 'blue', loading = false, error = false, onClick, compact = false }) => {
  const colorClasses: Record<string, { bg: string; text: string; border: string }> = {
    blue: {
      bg: 'bg-blue-100',
      text: 'text-blue-500',
      border: 'border-blue-200'
    },
    purple: {
      bg: 'bg-purple-100',
      text: 'text-purple-500',
      border: 'border-purple-200'
    },
    green: {
      bg: 'bg-green-100',
      text: 'text-green-500',
      border: 'border-green-200'
    }
  };

  const selectedColor = colorClasses[color] || colorClasses.blue;

  if (loading) {
    return (
      <div className={`bg-white ${compact ? 'p-3 sm:p-4 md:p-6' : 'p-6'} rounded-lg shadow-sm flex justify-between items-center animate-pulse`}>
        <div className="flex-1">
          <div className={`bg-gray-200 rounded ${compact ? 'h-3 w-16 mb-1' : 'h-4 w-24 mb-2'}`}></div>
          <div className={`bg-gray-200 rounded ${compact ? 'h-6 w-12' : 'h-8 w-16'}`}></div>
        </div>
        <div className={`rounded-lg ${selectedColor.bg} ${selectedColor.border} border ${compact ? 'p-2' : 'p-3'}`}>
          <div className={`${compact ? 'w-4 h-4' : 'w-6 h-6'} bg-gray-200 rounded`}></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white ${compact ? 'p-3 sm:p-4 md:p-6' : 'p-6'} rounded-lg shadow-sm flex justify-between items-center border border-red-200`}>
        <div className="flex-1">
          <p className={`${compact ? 'text-xs' : 'text-sm'} text-gray-500`}>{title}</p>
          <p className={`${compact ? 'text-xl' : 'text-3xl'} font-bold text-red-500`}>Error</p>
        </div>
        <div className={`rounded-lg ${selectedColor.bg} ${selectedColor.border} border ${compact ? 'p-2' : 'p-3'}`}>
          <svg className={`${compact ? 'w-4 h-4' : 'w-6 h-6'} ${selectedColor.text}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`bg-white ${compact ? 'p-3 sm:p-4 md:p-6' : 'p-6'} rounded-lg shadow-sm flex justify-between items-center transition duration-200 ${
        onClick ? 'hover:shadow-md cursor-pointer hover:bg-gray-50' : ''
      }`}
      onClick={onClick}
    >
      <div>
        <p className={`${compact ? 'text-xs' : 'text-sm'} text-gray-500`}>{title}</p>
        <p className={`${compact ? 'text-xl' : 'text-3xl'} font-bold text-gray-800`}>{(value as any)?.toLocaleString ? (value as any).toLocaleString() : value || '0'}</p>
      </div>
      <div className={`rounded-lg ${selectedColor.bg} ${selectedColor.border} border ${compact ? 'p-2' : 'p-3'}`}>
        {icon || (
          <svg className={`${compact ? 'w-4 h-4' : 'w-6 h-6'} ${selectedColor.text}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        )}
      </div>
    </div>
  );
};

export default StatCard;
