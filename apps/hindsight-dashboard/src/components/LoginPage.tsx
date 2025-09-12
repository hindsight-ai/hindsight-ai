import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import notificationService from '../services/notificationService';

const LoginPage: React.FC = () => {
  const { enterGuestMode, exitGuestMode } = useAuth();
  const location = useLocation();

  const handleSignIn = async () => {
    const host = window.location.hostname;
    const isLocal = host === 'localhost' || host === '127.0.0.1';

    if (isLocal) {
      // Ensure we are not in guest mode for auth checks
      try { exitGuestMode(); } catch {}
      // Dev experience: try backend dev user; if unavailable, guide the user
      try {
        const response = await fetch('/api/user-info', { credentials: 'include' });
        if (response.ok) {
          const userInfo = await response.json();
          if (userInfo?.authenticated) {
            window.location.href = '/dashboard';
            return;
          }
        }
        // Backend reachable but not authenticated: suggest running with dev compose or use Guest
        notificationService.showInfo('Authentication required. Use Guest mode in local dev, or start oauth2-proxy for full login.');
        return;
      } catch (error) {
        // Likely backend is not running or unreachable
        notificationService.showError('Backend unavailable (Bad Gateway). Start the backend: docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d');
        return;
      }
    }

    // Production OAuth flow
    const current = window.location.pathname + window.location.search + window.location.hash;
    const rdTarget = (location.pathname === '/login') ? '/dashboard' : current;
    const rd = encodeURIComponent(rdTarget);
    window.location.href = `/oauth2/sign_in?rd=${rd}`;
  };

  const handleGuest = () => {
    enterGuestMode();
    // Navigate to the dashboard so the app renders
    try { window.location.replace('/dashboard'); } catch { window.location.href = '/dashboard'; }
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
