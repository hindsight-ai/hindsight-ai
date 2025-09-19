import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import UserAccountButton from './UserAccountButton';
import OrganizationSwitcher from './OrganizationSwitcher';
import NotificationBell from './NotificationBell';
import { useAuth } from '../context/AuthContext';
import { useLocation } from 'react-router-dom';
import PageHeaderContext, { PageHeaderConfig } from '../context/PageHeaderContext';

interface MainContentProps {
  children: React.ReactNode;
  title: string;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  onOpenAbout?: () => void;
}

const MainContent: React.FC<MainContentProps> = ({ children, title, sidebarCollapsed, toggleSidebar, onOpenAbout }) => {
  const { guest } = useAuth();
  const location = useLocation();
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      try { scrollRef.current.scrollTo({ top: 0, left: 0, behavior: 'smooth' }); } catch { scrollRef.current.scrollTop = 0; }
    } else {
      try { window.scrollTo({ top: 0, left: 0, behavior: 'smooth' }); } catch {}
    }
  }, [location.pathname, location.search]);

  const [headerConfig, setHeaderConfig] = useState<PageHeaderConfig>({});

  const setHeaderContent = useCallback((config: PageHeaderConfig) => {
    setHeaderConfig(config);
  }, []);

  const clearHeaderContent = useCallback(() => {
    setHeaderConfig({});
  }, []);

  const headerContextValue = useMemo(() => ({
    setHeaderContent,
    clearHeaderContent,
    headerConfig
  }), [setHeaderContent, clearHeaderContent, headerConfig]);

  const defaultDescriptions = useMemo(() => ({
    Dashboard: 'Overview of your AI memory management system.',
    'Memory Blocks': 'Explore and manage the memory blocks captured across your organization.',
    Keywords: 'Maintain the keyword catalog that powers search and tagging.',
    Agents: 'Manage the agents connected to your workspace and oversee their access.',
    Analytics: 'Review conversation trends and performance insights for your assistants.',
    Consolidation: 'Audit and validate consolidation suggestions before they go live.',
    Archived: 'Browse previously archived memory blocks and restore them when needed.',
    Pruning: 'Identify low-value content and prune it to keep your memory store healthy.',
    Support: 'Find help resources and reach out for assistance with Hindsight AI.',
    Profile: 'Update your personal details and notification preferences.',
    Tokens: 'Create and manage API tokens for integrations and automations.',
    'Memory Block Detail': 'Inspect the full contents and metadata for a specific memory block.',
    'Consolidation Detail': 'Inspect a consolidation suggestion in depth before making changes.'
  }), []);

  const description = headerConfig.description ?? defaultDescriptions[title];
  const descriptionPadding = headerConfig.actions ? 'pr-24 sm:pr-32' : '';

  return (
    <PageHeaderContext.Provider value={headerContextValue}>
      <main className={`flex-1 flex flex-col overflow-hidden bg-gray-50 transition-all duration-300 ease-in-out ${sidebarCollapsed ? 'lg:p-4' : 'lg:p-4'}`}>
        <header className="p-4">
          <div className="max-w-[1200px] w-full mx-auto">
            {/* Row 1: organization left, actions right (single row across sizes) */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <button className="lg:hidden inline-flex items-center justify-center w-11 h-11 rounded-md border border-gray-300 text-gray-600 hover:bg-gray-100" onClick={toggleSidebar} aria-label="Open navigation">
                  <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
                </button>
                <div className="flex-1 min-w-0 md:max-w-[420px] lg:max-w-[420px]">
                  <OrganizationSwitcher />
                </div>
              </div>
              <div className="flex items-center gap-2 sm:gap-3 flex-nowrap justify-end">
                {guest && <span className="hidden sm:inline-flex px-2 py-0.5 text-[10px] sm:text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 border border-yellow-200">Guest Mode · Read-only</span>}
                <NotificationBell />
                <UserAccountButton />
              </div>
            </div>
          {/* Row 2: page title and actions */}
          <div className="mt-3 relative">
            <div className={`min-w-0 ${descriptionPadding}`}>
              <h2 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-800 truncate">{title}</h2>
              {description && (
                <p className="mt-2 text-sm text-gray-500 leading-relaxed break-words">
                  {description}
                </p>
              )}
            </div>
            {headerConfig.actions && (
              <div className="absolute top-0 right-0 flex items-center gap-2 whitespace-nowrap">
                {headerConfig.actions}
              </div>
            )}
          </div>
          </div>
        </header>
        <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto p-4">
          <div className="max-w-[1200px] w-full">
            {children}
          </div>
        </div>
      </main>
    </PageHeaderContext.Provider>
  );
};

export default MainContent;
