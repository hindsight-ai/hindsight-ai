import React, { useMemo } from 'react';
import { useLocation } from 'react-router-dom';

const BetaAccessGrantConfirmationPage: React.FC = () => {
  const location = useLocation();
  const { email, status } = useMemo(() => {
    try {
      const params = new URLSearchParams(location.search);
      return {
        email: params.get('email') || '',
        status: params.get('status') || '',
      };
    } catch {
      return { email: '', status: '' };
    }
  }, [location.search]);

  const isAlreadyGranted = status === 'already';

  const handleGoToDashboard = () => {
    const target = '/dashboard';
    try {
      window.location.replace(target);
    } catch {
      window.location.href = target;
    }
  };

  const handleViewPending = () => {
    const target = '/beta-access/pending';
    try {
      window.location.replace(target);
    } catch {
      window.location.href = target;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-sky-100 flex items-center justify-center p-4">
      <div className="max-w-xl w-full bg-white rounded-2xl shadow-2xl p-10 text-center">
        <div className="mb-8">
          <div className="mx-auto w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mb-5">
            <svg className="w-10 h-10 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4" />
              <circle cx="12" cy="12" r="9" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-3">
            {isAlreadyGranted ? 'Access Already Granted' : 'Beta Access Granted'}
          </h1>
          <p className="text-gray-600">
            {email ? (
              isAlreadyGranted ? (
                <>
                  Access for <span className="font-medium text-gray-900">{email}</span> was already granted earlier. No further action is required.
                </>
              ) : (
                <>
                  Access for <span className="font-medium text-gray-900">{email}</span> has been approved. They can now sign in and start using Hindsight AI.
                </>
              )
            ) : (
              isAlreadyGranted
                ? 'This beta access request had already been approved earlier. You are all set.'
                : 'The beta access request has been approved. The recipient can now sign in and use Hindsight AI.'
            )}
          </p>
        </div>

        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-6 text-left mb-8">
          <h2 className="text-lg font-semibold text-emerald-800 mb-2">What happens next?</h2>
          <ul className="text-sm text-emerald-900 space-y-2 list-disc list-inside">
            {isAlreadyGranted ? (
              <>
                <li>The requester already has access—no additional steps are required.</li>
                <li>You can review any remaining pending requests when you are ready.</li>
              </>
            ) : (
              <>
                <li>The requester receives an email letting them know access is ready.</li>
                <li>You can continue reviewing other requests or head back to the dashboard.</li>
              </>
            )}
          </ul>
        </div>

        <div className="flex flex-col sm:flex-row sm:justify-center sm:space-x-4 space-y-3 sm:space-y-0">
          <button
            onClick={handleViewPending}
            className="inline-flex justify-center items-center px-5 py-3 bg-white text-emerald-700 border border-emerald-300 text-sm font-medium rounded-lg hover:bg-emerald-50 transition-colors duration-200"
          >
            View Pending Requests
          </button>
          <button
            onClick={handleGoToDashboard}
            className="inline-flex justify-center items-center px-5 py-3 bg-emerald-600 text-white text-sm font-medium rounded-lg shadow-sm hover:bg-emerald-700 transition-colors duration-200"
          >
            Go to Dashboard
          </button>
        </div>

        <div className="mt-10 pt-6 border-t border-gray-200">
          <p className="text-xs uppercase tracking-wide text-gray-400">Hindsight AI • Beta Program Admin Tools</p>
        </div>
      </div>
    </div>
  );
};

export default BetaAccessGrantConfirmationPage;
