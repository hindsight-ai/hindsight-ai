import React, { useState } from 'react';
import Sidebar from './Sidebar';
import MainContent from './MainContent';
import { VITE_DEV_MODE } from '../lib/viteEnv';

interface LayoutProps {
  title: string;
  children: React.ReactNode;
  onOpenAbout?: () => void;
  onToggleDebugPanel?: () => void;
  onOpenGetStarted?: () => void;
}

const Layout: React.FC<LayoutProps> = ({ children, title, onOpenAbout, onToggleDebugPanel, onOpenGetStarted }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const toggleSidebar = () => setSidebarOpen(o => !o);
  const closeSidebar = () => setSidebarOpen(false);
  const handleSidebarCollapse = (collapsed: boolean) => setSidebarCollapsed(collapsed);

  return (
    // No outer overflow-hidden / flex-column wrap: the document is now the
    // scroller (RFC 0002 M1). Mobile address-bar tap, browser scroll
    // restoration, and overscroll bounce all need the body to be the
    // scrolling element. Sidebar stays fixed; main flows naturally.
    <div className="min-h-[100dvh] bg-gray-100">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={closeSidebar}
        onCollapseChange={handleSidebarCollapse}
        onToggleDebugPanel={VITE_DEV_MODE ? onToggleDebugPanel : undefined}
      />
      <div className={sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'}>
        <MainContent
          title={title}
          toggleSidebar={toggleSidebar}
          onOpenAbout={onOpenAbout}
          onOpenHelp={onOpenGetStarted}
        >
          {children}
        </MainContent>
      </div>
    </div>
  );
};

export default Layout;
