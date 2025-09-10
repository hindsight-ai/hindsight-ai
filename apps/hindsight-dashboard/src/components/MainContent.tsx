import React, { useEffect, useRef, useState } from 'react';
import UserAccountButton from './UserAccountButton';
import OrganizationSwitcher from './OrganizationSwitcher';
import { useAuth } from '../context/AuthContext';
import { useLocation } from 'react-router-dom';

interface MainContentProps {
  children: React.ReactNode;
  title: string;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

const MainContent: React.FC<MainContentProps> = ({ children, title, sidebarCollapsed, toggleSidebar }) => {
  const { guest } = useAuth();
  const location = useLocation();
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState<number>(1);

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
      if (typeof window !== 'undefined' && window.innerWidth < 640) setScale(0.75);
    } catch {}
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      try { scrollRef.current.scrollTo({ top: 0, left: 0, behavior: 'smooth' }); } catch { scrollRef.current.scrollTop = 0; }
    } else {
      try { window.scrollTo({ top: 0, left: 0, behavior: 'smooth' }); } catch {}
    }
  }, [location.pathname, location.search]);

  const updateScale = (val: number) => {
    setScale(val);
    try { localStorage.setItem('UI_SCALE', String(val)); } catch {}
  };

  return (
    <main className={`flex-1 flex flex-col overflow-hidden bg-gray-50 transition-all duration-300 ease-in-out ${sidebarCollapsed ? 'lg:p-4' : 'lg:p-4'}`}>
      <header className="p-4">
        <div className="max-w-[1200px] w-full">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <button className="lg:hidden inline-flex items-center justify-center w-10 h-10 rounded-md border border-gray-300 text-gray-600 hover:bg-gray-100" onClick={toggleSidebar} aria-label="Open navigation">
                <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
              </button>
              <h2 className="text-lg sm:text-2xl font-bold text-gray-800 truncate">{title}</h2>
            </div>
            <div className="flex items-center gap-2 sm:gap-3">
              <OrganizationSwitcher />
            </div>
            <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
              <select className="border border-gray-300 rounded-md px-2 py-1 text-xs sm:text-sm bg-white" value={String(scale)} onChange={e => updateScale(parseFloat(e.target.value))} aria-label="Display scale" title="Display scale">
                <option value="1">100%</option>
                <option value="0.75">75%</option>
                <option value="0.5">50%</option>
              </select>
              {guest && <span className="px-2 py-0.5 text-[10px] sm:text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 border border-yellow-200">Guest Mode · Read-only</span>}
              <UserAccountButton />
            </div>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-gray-500 truncate">{title === 'Dashboard' ? 'Overview of your AI memory management system' : `Manage your ${title.toLowerCase()}`}</p>
        </div>
      </header>
      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto p-4">
        <div className="max-w-[1200px] w-full">
          <div className="transform-gpu origin-top-left" style={{ transform: `scale(${scale})`, width: '100%' }}>
            {children}
          </div>
        </div>
      </div>
    </main>
  );
};

export default MainContent;
