import React, { useEffect, useState } from 'react';
import UserAccountButton from './UserAccountButton';
import { useAuth } from '../context/AuthContext';

const MainContent = ({ children, title, sidebarCollapsed, toggleSidebar }) => {
  const { guest } = useAuth();

  // UI scale control
  const [scale, setScale] = useState(1);
  useEffect(() => {
    try {
      const savedStr = localStorage.getItem('UI_SCALE');
      if (savedStr) {
        const saved = parseFloat(savedStr);
        if (saved && saved > 0.3 && saved <= 1) {
          setScale(saved);
          return;
        }
      }
      // Default to 75% on small screens if not previously chosen
      if (typeof window !== 'undefined' && window.innerWidth < 640) {
        setScale(0.75);
      }
    } catch {}
  }, []);
  const updateScale = (val) => {
    setScale(val);
    try { localStorage.setItem('UI_SCALE', String(val)); } catch {}
  };

  return (
    <main className={`flex-1 flex flex-col overflow-hidden bg-gray-50 transition-all duration-300 ease-in-out ${
      sidebarCollapsed ? 'lg:p-4' : 'lg:p-4'
    }`}>
      {/* Header */}
      <header className="p-4">
        <div className="max-w-[1200px] w-full">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
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
            <h2 className="text-lg sm:text-2xl font-bold text-gray-800 truncate">{title}</h2>
          </div>
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            {/* Scale selector (no label) */}
            <select
              className="border border-gray-300 rounded-md px-2 py-1 text-xs sm:text-sm bg-white"
              value={String(scale)}
              onChange={(e) => updateScale(parseFloat(e.target.value))}
              aria-label="Display scale"
              title="Display scale"
            >
              <option value="1">100%</option>
              <option value="0.75">75%</option>
              <option value="0.5">50%</option>
            </select>
            {guest && (
              <span className="px-2 py-0.5 text-[10px] sm:text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 border border-yellow-200">
                Guest Mode · Read-only
              </span>
            )}
            <UserAccountButton />
          </div>
        </div>
        <p className="mt-1 text-xs sm:text-sm text-gray-500 truncate">
          {title === 'Dashboard'
            ? 'Overview of your AI memory management system'
            : `Manage your ${title.toLowerCase()}`
          }
        </p>
        </div>
      </header>

      {/* Scaled content wrapper with horizontal scroll on small screens */}
      <div className="flex-1 overflow-auto p-4">
        <div className="max-w-[1200px] w-full">
          <div
            className="transform-gpu origin-top-left"
            style={{ transform: `scale(${scale})`, width: '100%' }}
          >
            {children}
          </div>
        </div>
      </div>
    </main>
  );
};

export default MainContent;
