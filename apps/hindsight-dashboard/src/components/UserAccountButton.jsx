import React, { useState, useEffect } from 'react';
import authService from '../api/authService';

const UserAccountButton = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showDropdown, setShowDropdown] = useState(false);

  useEffect(() => {
    fetchUserInfo();
  }, []);

  const fetchUserInfo = async () => {
    try {
      const userInfo = await authService.getCurrentUser();
      setUser(userInfo);
    } catch (error) {
      console.error('Error fetching user info:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    // Redirect to logout URL or handle logout logic
    window.location.href = 'https://auth.hindsight-ai.com/oauth2/sign_out?rd=https%3A%2F%2Fapp.hindsight-ai.com';
  };

  if (loading) {
    return (
      <div className="w-8 h-8 bg-gray-200 rounded-full animate-pulse"></div>
    );
  }

  if (!user || !user.authenticated) {
    return (
      <button
        onClick={() => window.location.href = 'https://auth.hindsight-ai.com/oauth2/sign_in?rd=https%3A%2F%2Fapp.hindsight-ai.com'}
        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition duration-200"
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
        <span className="text-sm text-gray-700 hidden md:block">
          {user.email || user.user}
        </span>
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
          <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-20">
            <div className="px-4 py-3 border-b border-gray-200">
              <p className="text-sm font-medium text-gray-900">
                {user.email || user.user}
              </p>
              <p className="text-xs text-gray-500">Signed in</p>
            </div>
            <div className="py-1">
              <button
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition duration-200"
              >
                Sign Out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default UserAccountButton;
