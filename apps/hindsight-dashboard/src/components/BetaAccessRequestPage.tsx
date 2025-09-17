import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api/http';
import notificationService from '../services/notificationService';

const BetaAccessRequestPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [isDisclaimerAccepted, setIsDisclaimerAccepted] = useState(false);
  const { user, loading, refresh } = useAuth() as any;

  const accountEmail = useMemo(() => {
    const raw = (user as any)?.email;
    return typeof raw === 'string' ? raw.trim() : '';
  }, [user]);

  useEffect(() => {
    if (accountEmail) {
      setEmail(accountEmail);
    } else {
      setEmail('');
    }
  }, [accountEmail]);

  const isSubmitDisabled = isSubmitting || !email.trim();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setError('Unable to determine your account email. Please refresh and try again.');
      return;
    }
    if (!isDisclaimerAccepted) {
      setError('You must accept the beta program disclaimer to proceed');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const response = await apiFetch('/beta-access/request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        noScope: true,
        body: JSON.stringify({ email: email.trim() }),
      });

      if (response.ok) {
        setIsSubmitted(true);
        notificationService.showSuccess('Beta access request sent! Check your email for confirmation.');
        if (typeof refresh === 'function') {
          try {
            await refresh();
          } catch (refreshError) {
            // Intentionally swallow refresh errors so the confirmation screen still renders
          }
        }
      } else if (response.status === 400) {
        setError('You have already requested beta access. Please wait for approval.');
        notificationService.showWarning('You have already requested beta access. We will reach out once it is reviewed.');
      } else {
        setError('Failed to submit request. Please try again.');
        notificationService.showError('Unable to submit your beta access request. Please try again.');
      }
    } catch (err) {
      setError('Network error. Please check your connection and try again.');
      notificationService.showNetworkError();
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-xl p-8 text-center">
          <div className="mb-6">
            <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Request Submitted!
            </h1>
            <p className="text-gray-600 mb-6">
              Your request to join the Hindsight AI beta has been submitted successfully.
            </p>
          </div>

          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-center mb-2">
              <svg className="w-5 h-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <span className="text-sm font-medium text-green-800">
                Check your email
              </span>
            </div>
            <p className="text-sm text-green-700">
              You'll receive a confirmation email and status updates.
            </p>
          </div>

          <p className="text-sm text-gray-500">
            Your request will be reviewed within 24 hours.
          </p>

          <div className="mt-8 pt-6 border-t border-gray-200">
            <p className="text-xs text-gray-400">
              Hindsight AI - Memory Intelligence Hub
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-xl p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Join the Beta
          </h1>
          <p className="text-gray-600">
            Request access to the Hindsight AI beta program
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
              Email Address
            </label>
            <input
              type="email"
              id="email"
              value={email}
              readOnly
              className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent cursor-not-allowed"
              placeholder={loading ? 'Loading account email...' : 'your.email@example.com'}
              required
            />
            </div>

          <div>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
              <h3 className="text-sm font-medium text-yellow-800 mb-2">
                Beta Program Disclaimer
              </h3>
              <p className="text-sm text-yellow-700">
                Hindsight AI is currently in beta. By requesting access, you acknowledge that:
              </p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-sm text-yellow-700">
                <li>Data confidentiality is not guaranteed.</li>
                <li>Data loss or corruption may occur.</li>
                <li>The application is not guaranteed to be secure from cyber threats.</li>
                <li>Functionality may be incomplete or unstable.</li>
                <li>Application availability is not guaranteed and is susceptible to downtime at any moment.</li>
              </ul>
              <p className="text-sm text-yellow-700 mt-2">
                Use at your own risk. We are not liable for any data-related issues or service interruptions during the beta phase.
              </p>
            </div>
            <div className="flex items-center">
              <input
                type="checkbox"
                id="disclaimer"
                checked={isDisclaimerAccepted}
                onChange={(e) => setIsDisclaimerAccepted(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="disclaimer" className="ml-2 block text-sm text-gray-700">
                I understand and accept the beta program disclaimer
              </label>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="w-full flex items-center justify-center px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
          >
            {isSubmitting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Submitting...
              </>
            ) : (
              <>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
                Request Beta Access
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-gray-200 text-center">
          <p className="text-sm text-gray-500 mb-2">
            What is Hindsight AI?
          </p>
          <p className="text-xs text-gray-400">
            An intelligent memory management system that helps organize and optimize your AI conversations and knowledge.
          </p>
        </div>
      </div>
    </div>
  );
};

export default BetaAccessRequestPage;
