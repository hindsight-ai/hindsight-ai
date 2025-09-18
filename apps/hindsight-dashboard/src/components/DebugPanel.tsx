import React from 'react';
import notificationService from '../services/notificationService';
import { VITE_DEV_MODE } from '../lib/viteEnv';

interface DebugPanelProps {
  visible?: boolean;
}

const DebugPanel: React.FC<DebugPanelProps> = ({ visible = false }) => {
  // Only show in development mode OR when explicitly made visible
  const isDevMode = VITE_DEV_MODE;
  if (!isDevMode && !visible) {
    return null;
  }

  const showSuccessToast = () => {
    notificationService.showSuccess('This is a success notification! Operation completed successfully.');
  };

  const showInfoToast = () => {
    notificationService.showInfo('This is an info notification! Here is some useful information.');
  };

  const showWarningToast = () => {
    notificationService.showWarning('This is a warning notification! Please review this important message.');
  };

  const showErrorToast = () => {
    notificationService.showError('This is an error notification! Something went wrong and needs attention.');
  };

  const showNetworkErrorToast = () => {
    notificationService.showNetworkError();
  };

  const show403ErrorToast = () => {
    notificationService.show403Error('access this feature');
  };

  const show404ErrorToast = () => {
    notificationService.show404Error('page');
  };

  const show500ErrorToast = () => {
    notificationService.show500Error();
  };

  return (
    <div className="fixed bottom-4 right-4 z-50 bg-white border border-gray-300 rounded-lg shadow-lg p-4 max-w-xs">
      <div className="text-xs font-semibold text-gray-700 mb-3 text-center">
        🛠️ Debug Panel
      </div>
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={showSuccessToast}
          className="px-3 py-2 text-xs bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
          title="Show success toast"
        >
          ✅ Success
        </button>
        <button
          onClick={showInfoToast}
          className="px-3 py-2 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
          title="Show info toast"
        >
          ℹ️ Info
        </button>
        <button
          onClick={showWarningToast}
          className="px-3 py-2 text-xs bg-yellow-500 text-white rounded hover:bg-yellow-600 transition-colors"
          title="Show warning toast"
        >
          ⚠️ Warning
        </button>
        <button
          onClick={showErrorToast}
          className="px-3 py-2 text-xs bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
          title="Show error toast"
        >
          ❌ Error
        </button>
        <button
          onClick={showNetworkErrorToast}
          className="px-3 py-2 text-xs bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors col-span-2"
          title="Show network error toast"
        >
          🌐 Network Error
        </button>
        <button
          onClick={show403ErrorToast}
          className="px-3 py-2 text-xs bg-orange-500 text-white rounded hover:bg-orange-600 transition-colors"
          title="Show 403 error toast"
        >
          🚫 403
        </button>
        <button
          onClick={show404ErrorToast}
          className="px-3 py-2 text-xs bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors"
          title="Show 404 error toast"
        >
          🔍 404
        </button>
        <button
          onClick={show500ErrorToast}
          className="px-3 py-2 text-xs bg-red-700 text-white rounded hover:bg-red-800 transition-colors col-span-2"
          title="Show 500 error toast"
        >
          💥 500 Server Error
        </button>
      </div>
      <div className="mt-3 text-xs text-gray-500 text-center">
        Dev Mode Only
      </div>
    </div>
  );
};

export default DebugPanel;
