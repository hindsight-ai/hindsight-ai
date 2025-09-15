import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import OrganizationManagement from './OrganizationManagement';

const UserAccountButton: React.FC = () => {
  const { user, loading } = useAuth();
  const [showDropdown, setShowDropdown] = useState(false);
  const [showOrgManagement, setShowOrgManagement] = useState(false);

  const handleLogout = () => {
    // Check if we're in dev mode
    if (user?.email === 'dev@localhost') {
      // In dev mode, just refresh the page to restart auth
      window.location.href = '/';
      return;
    }
    
    // Production logout via OAuth
    const rd = encodeURIComponent(window.location.origin);
    window.location.href = `/oauth2/sign_out?rd=${rd}`;
  };

  if (loading) {
    return (
      <div className="w-8 h-8 bg-gray-200 rounded-full animate-pulse"></div>
    );
  }

  if (!user || !user.authenticated) {
    return (
      <button
        onClick={() => {
          const rd = encodeURIComponent(window.location.pathname + window.location.search + window.location.hash);
          window.location.href = `/oauth2/sign_in?rd=${rd}`;
        }}
        className="px-3 py-1.5 sm:px-4 sm:py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition duration-200 text-sm sm:text-base"
      >
        Sign In
      </button>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition duration-200"
      >
        <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white font-semibold">
          {user.email ? user.email.charAt(0).toUpperCase() : 'U'}
        </div>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${showDropdown ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {showDropdown && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowDropdown(false)}
          ></div>
          <div className="absolute right-0 mt-2 w-60 bg-white rounded-lg shadow-lg border border-gray-200 z-20">
            <div className="px-4 py-3 border-b border-gray-200">
              <p className="text-sm font-medium text-gray-900">
                {user.email || user.display_name || 'User'}
              </p>
              <p className="text-xs text-gray-500">
                {user.email === 'dev@localhost' ? 'Development Mode' : 'Signed in'}
                {user.is_superadmin && <span className="ml-1 px-1 bg-red-100 text-red-800 rounded text-xs">Admin</span>}
              </p>
            </div>
            <div className="py-1">
              <button
                onClick={() => {
                  setShowDropdown(false);
                  try { window.history.pushState(null, '', '/profile'); } catch {}
                  window.location.href = '/profile';
                }}
                className="w-full flex items-center gap-2 text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition duration-200"
              >
                {/* User icon */}
                <svg className="w-4 h-4 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M4 21v-2a4 4 0 0 1 3-3.87" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                Edit Profile
              </button>
              <button
                onClick={() => {
                  setShowDropdown(false);
                  try { window.history.pushState(null, '', '/tokens'); } catch {}
                  window.location.href = '/tokens';
                }}
                className="w-full flex items-center gap-2 text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition duration-200"
              >
                {/* API Tokens icon */}
                <svg className="w-4 h-4 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 5v14" />
                  <path d="M5 12h14" />
                </svg>
                API Tokens
              </button>
              <button
                onClick={() => {
                  setShowOrgManagement(true);
                  setShowDropdown(false);
                }}
                className="w-full flex items-center gap-2 text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition duration-200"
              >
                {/* Organization icon */}
                <svg className="w-4 h-4 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 9l9-6 9 6v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                  <path d="M9 22V12h6v10" />
                </svg>
                Manage Organizations
              </button>
              <a
                href="https://buymeacoffee.com/jeanibarz"
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setShowDropdown(false)}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition duration-200"
              >
                {/* Coffee icon */}
                <svg className="w-4 h-4 text-amber-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 8h13a4 4 0 010 8H16a5 5 0 01-5 5H8a5 5 0 01-5-5V8z" />
                  <path d="M16 8h2a3 3 0 010 6h-2" />
                  <path d="M6 1s1 1 0 2 1 1 0 2 1 1 0 2" />
                </svg>
                Support / Buy me a coffee
              </a>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition duration-200"
              >
                {/* Sign out icon */}
                <svg className="w-4 h-4 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <path d="M16 17l5-5-5-5" />
                  <path d="M21 12H9" />
                </svg>
                Sign Out
              </button>
            </div>
          </div>
        </>
      )}
      
      {showOrgManagement && (
        <OrganizationManagement onClose={() => setShowOrgManagement(false)} />
      )}
    </div>
  );
};

export default UserAccountButton;
