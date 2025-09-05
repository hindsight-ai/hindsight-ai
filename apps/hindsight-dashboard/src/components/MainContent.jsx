import React, { useEffect, useState } from 'react';
import UserAccountButton from './UserAccountButton';
import { useAuth } from '../context/AuthContext';

const MainContent = ({ children, title, sidebarCollapsed, toggleSidebar }) => {
  const { guest } = useAuth();

  // UI scale control
  const [scale, setScale] = useState(1);
  useEffect(() => {
    try {
      const saved = parseFloat(localStorage.getItem('UI_SCALE') || '1');
      if (saved && saved > 0.3 && saved <= 1) setScale(saved);
    } catch {}
  }, []);
  const updateScale = (val) => {
    setScale(val);
    try { localStorage.setItem('UI_SCALE', String(val)); } catch {}
  };

  return (
    <main className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 ease-in-out ${
      sidebarCollapsed ? 'lg:p-4' : 'lg:p-4'
    }`}>
      {/* Header */}
      <header className="p-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          {/* Mobile Hamburger */}
          <button
            className="lg:hidden inline-flex items-center justify-center w-10 h-10 rounded-md border border-gray-300 text-gray-600 hover:bg-gray-100"
            onClick={toggleSidebar}
            aria-label="Open navigation"
          >
            <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div>
            <h2 className="text-2xl font-bold text-gray-800">{title}</h2>
            <p className="text-gray-500">
              {title === 'Dashboard'
                ? 'Overview of your AI memory management system'
                : `Manage your ${title.toLowerCase()}`
              }
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Scale selector */}
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <span className="hidden sm:inline">Display:</span>
            <select
              className="border border-gray-300 rounded-md px-2 py-1 text-sm bg-white"
              value={String(scale)}
              onChange={(e) => updateScale(parseFloat(e.target.value))}
            >
              <option value="1">100%</option>
              <option value="0.75">75%</option>
              <option value="0.5">50%</option>
            </select>
          </label>
          {guest && (
            <span className="px-3 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 border border-yellow-200">
              Guest Mode · Read-only
            </span>
          )}
          <UserAccountButton />
        </div>
      </header>

      {/* Scaled content wrapper with horizontal scroll on small screens */}
      <div className="flex-1 overflow-auto p-4">
        <div
          className="transform-gpu origin-top-left"
          style={{ transform: `scale(${scale})`, width: `${100 / scale}%` }}
        >
          {children}
        </div>
      </div>
    </main>
  );
};

export default MainContent;
