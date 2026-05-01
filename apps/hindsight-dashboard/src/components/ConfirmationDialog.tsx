import React from 'react';

interface ConfirmationDialogProps {
  title: string;
  body: string;
  confirmLabel: string;
  cancelLabel?: string;
  confirmClassName?: string;
  iconContent?: React.ReactNode;
  iconBgClass?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmationDialog: React.FC<ConfirmationDialogProps> = ({
  title,
  body,
  confirmLabel,
  cancelLabel = 'Cancel',
  confirmClassName = 'px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700',
  iconContent,
  iconBgClass = 'bg-gray-100',
  onConfirm,
  onCancel,
}) => (
  <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-60">
    <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
      <div className="flex items-center mb-4">
        {iconContent && (
          <div className={`flex-shrink-0 w-10 h-10 ${iconBgClass} rounded-full flex items-center justify-center`}>
            {iconContent}
          </div>
        )}
        <div className={iconContent ? 'ml-3' : ''}>
          <h3 className="text-lg font-medium text-gray-900">{title}</h3>
        </div>
      </div>
      <div className="mb-4">
        <p className="text-sm text-gray-500">{body}</p>
      </div>
      <div className="flex justify-end space-x-3">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
        >
          {cancelLabel}
        </button>
        <button onClick={onConfirm} className={confirmClassName}>
          {confirmLabel}
        </button>
      </div>
    </div>
  </div>
);

export default ConfirmationDialog;
