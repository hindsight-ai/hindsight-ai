import React from 'react';
import { useAuth } from '../context/AuthContext';

const LoginPage = () => {
  const { enterGuestMode, exitGuestMode } = useAuth();

  const handleSignIn = () => {
    try { exitGuestMode(); } catch {}
    const rd = encodeURIComponent(window.location.pathname + window.location.search + window.location.hash);
    window.location.href = `/oauth2/sign_in?rd=${rd}`;
  };

  const handleGuest = () => {
    enterGuestMode();
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-start justify-center pt-8">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-800 mb-4">AI Agent Memory Dashboard</h1>
        <div className="bg-white p-8 rounded-lg shadow-md max-w-md space-y-4">
          <h2 className="text-xl font-semibold">Authentication Required</h2>
          <p className="text-gray-600">Sign in to access your data, or explore a read-only guest tour.</p>
          <div className="flex gap-3 justify-center">
            <button
              className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg transition duration-200"
              onClick={handleSignIn}
            >
              Sign In
            </button>
            <button
              className="bg-gray-100 hover:bg-gray-200 text-gray-800 px-6 py-2 rounded-lg transition duration-200 border"
              onClick={handleGuest}
            >
              Explore as Guest
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;

