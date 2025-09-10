import React from 'react';

const formatDuration = (ms: number): string => {
  if (!ms || ms < 0) return '';
  const totalSeconds = Math.ceil(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
};

interface ProcessingDialogProps {
  isOpen: boolean;
  title?: string;
  subtitle?: string;
  progress?: number;
  processed?: number;
  total?: number;
  elapsedMs?: number;
  etaMs?: number;
  cancellable?: boolean;
  onCancel?: () => void;
}

const ProcessingDialog: React.FC<ProcessingDialogProps> = ({
  isOpen,
  title = 'Processing',
  subtitle,
  progress = 0,
  processed = 0,
  total = 0,
  elapsedMs = 0,
  etaMs = 0,
  cancellable = true,
  onCancel,
}) => {
  if (!isOpen) return null;

  const percent = Math.min(100, Math.max(0, Math.round(progress * 100)));

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-[100]">
      <div className="bg-white rounded-lg shadow-xl w-11/12 max-w-xl p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            {subtitle && <p className="text-sm text-gray-600 mt-1">{subtitle}</p>}
          </div>
          {cancellable && (
            <button
              onClick={onCancel}
              className="text-gray-400 hover:text-gray-600"
              title="Cancel"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        <div className="mt-2">
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all"
              style={{ width: `${percent}%` }}
            />
          </div>
          <div className="mt-3 flex items-center justify-between text-sm text-gray-600">
            <span>
              {processed}/{total} processed
            </span>
            <span>
              {percent}%
            </span>
          </div>

          <div className="mt-2 grid grid-cols-2 gap-4 text-xs text-gray-500">
            <div>
              <div className="font-medium text-gray-700">Elapsed</div>
              <div>{formatDuration(elapsedMs)}</div>
            </div>
            <div>
              <div className="font-medium text-gray-700">ETA</div>
              <div>{formatDuration(etaMs)}</div>
            </div>
          </div>
        </div>

        {cancellable && (
          <div className="mt-6 flex justify-end">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProcessingDialog;
