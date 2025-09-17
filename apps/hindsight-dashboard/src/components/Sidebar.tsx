import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { VITE_DEV_MODE } from '../lib/viteEnv';
import { useAuth } from '../context/AuthContext';
import notificationService from '../services/notificationService';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onCollapseChange?: (collapsed: boolean) => void;
  onToggleDebugPanel?: () => void;
}

interface NavItem {
  name: string;
  path: string;
  icon: React.ReactNode;
  disabled?: boolean;
  disabledMessage?: string;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose, onCollapseChange, onToggleDebugPanel }) => {
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const { features } = useAuth();

  const handleCollapseToggle = () => {
    const newCollapsedState = !isCollapsed;
    setIsCollapsed(newCollapsedState);
    onCollapseChange?.(newCollapsedState);
  };

  const navigationItems: NavItem[] = [
    { name: 'Dashboard', path: '/dashboard', icon: (<svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>) },
    { name: 'Memory Blocks', path: '/memory-blocks', icon: (<svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4M4 7s-.5 1 .5 2M20 7s.5 1-.5 2m-19 5s.5-1-.5-2m19 5s-.5-1 .5-2" /></svg>) },
    { name: 'Keywords', path: '/keywords', icon: (<svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>) },
    { name: 'Agents', path: '/agents', icon: (<svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M15 21a6 6 0 00-9-5.197M15 21a6 6 0 00-9-5.197" /></svg>) },
    { name: 'Analytics', path: '/analytics', icon: (<svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>) },
    {
      name: 'Consolidation',
      path: '/consolidation-suggestions',
      icon: (<svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>),
      disabled: !features.consolidationEnabled,
      disabledMessage: 'Feature coming soon',
    },
    {
      name: 'Archived',
      path: '/archived-memory-blocks',
      icon: (<svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" /></svg>),
      disabled: !features.archivedEnabled,
      disabledMessage: 'Feature coming soon',
    },
    { name: 'AI Optimization', path: '/memory-optimization-center', icon: (<svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>) },
    {
      name: 'Pruning',
      path: '/pruning-suggestions',
      icon: (<svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>),
      disabled: !features.pruningEnabled,
      disabledMessage: 'Feature coming soon',
    },
  // Only include Debug Panel in development mode
  ...(VITE_DEV_MODE ? [{ name: 'Debug Panel', path: '#', icon: (<svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>) }] : [])
  ];

  const isActive = (path: string) => location.pathname === path || location.pathname.startsWith(path + '/');

  return (
    <>
      {isOpen && <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 lg:hidden" onClick={onClose} />}
      <aside className={`fixed top-0 left-0 h-screen z-50 ${isCollapsed ? 'w-16' : 'w-64'} flex-shrink-0 bg-[#0F172A] text-gray-300 flex flex-col overflow-y-auto transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}>
        <div className="h-16 flex items-center justify-between px-4 pt-4 pb-2 border-b border-gray-700">
          <div className={`flex flex-col transition-all duration-200 ${isCollapsed ? 'opacity-0 w-0 overflow-hidden' : 'opacity-100 w-auto'}`}>
            <h1 className="text-lg font-bold text-white leading-tight">Hindsight AI</h1>
            <p className="text-xs text-gray-400 leading-tight">Memory Intelligence Hub</p>
          </div>
          <button onClick={handleCollapseToggle} className="flex items-center justify-center w-8 h-8 rounded-lg hover:bg-gray-700 transition-colors duration-200 text-gray-400 hover:text-white" title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}>
            <svg className={`w-4 h-4 transition-transform duration-200 ${isCollapsed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        </div>
        <nav className="flex-1 px-3 py-6 space-y-1">
          {navigationItems.map(item => {
            if (item.name === 'Debug Panel') {
              return (
                <button
                  key={item.path}
                  onClick={() => {
                    onToggleDebugPanel?.();
                    onClose();
                  }}
                  className={`flex items-center ${isCollapsed ? 'justify-center px-3' : 'px-3'} py-3 text-sm font-medium rounded-lg transition-all duration-200 relative overflow-hidden hover:bg-gray-700 text-gray-300 hover:text-white`}
                  title={isCollapsed ? item.name : ''}
                >
                  <div className="flex items-center flex-1 min-w-0">
                    <div className="flex-shrink-0">{item.icon}</div>
                    <span className={`ml-3 transition-all duration-200 whitespace-nowrap ${isCollapsed ? 'opacity-0 w-0 overflow-hidden' : 'opacity-100 w-auto'}`}>{item.name}</span>
                  </div>
                </button>
              );
            }
            const disabledClasses = item.disabled ? 'opacity-50 cursor-not-allowed' : '';
            const baseClasses = isActive(item.path)
              ? 'bg-blue-600 text-white shadow-lg'
              : 'hover:bg-gray-700 text-gray-300 hover:text-white';
            const handleClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
              if (item.disabled) {
                event.preventDefault();
                event.stopPropagation();
                notificationService.showInfo(item.disabledMessage || 'Feature coming soon');
                onClose();
                return;
              }
              onClose();
            };
            return (
              <Link
                key={item.path}
                to={item.disabled ? '#' : item.path}
                className={`flex items-center ${isCollapsed ? 'justify-center px-3' : 'px-3'} py-3 text-sm font-medium rounded-lg transition-all duration-200 relative overflow-hidden ${baseClasses} ${disabledClasses}`}
                onClick={handleClick}
                title={isCollapsed ? item.name : ''}
                aria-disabled={item.disabled ? 'true' : undefined}
              >
                <div className="flex items-center flex-1 min-w-0">
                  <div className="flex-shrink-0">{item.icon}</div>
                  <span className={`ml-3 transition-all duration-200 whitespace-nowrap ${isCollapsed ? 'opacity-0 w-0 overflow-hidden' : 'opacity-100 w-auto'}`}>{item.name}</span>
                </div>
              </Link>
            );
          })}
        </nav>
        <div className={`px-4 py-4 border-t border-gray-700 transition-all duration-200 ${isCollapsed ? 'opacity-0 w-0 overflow-hidden' : 'opacity-100 w-auto'}`}>
          <p className="text-xs text-gray-400 leading-tight">AI-Powered Memory Dashboard</p>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
