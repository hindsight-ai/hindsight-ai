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
    <div className="flex min-h-[100dvh] bg-gray-100 overflow-hidden">
      <div className="fixed left-0 top-0 h-full z-10">
        <Sidebar 
          isOpen={sidebarOpen} 
          onClose={closeSidebar} 
          onCollapseChange={handleSidebarCollapse} 
          onToggleDebugPanel={VITE_DEV_MODE ? onToggleDebugPanel : undefined} 
        />
      </div>
      <div className={`flex-1 flex flex-col min-h-0 overflow-hidden ${sidebarCollapsed ? 'lg:ml-16 ml-0' : 'lg:ml-64 ml-0'}`}>
        <MainContent
          title={title}
          toggleSidebar={toggleSidebar}
          sidebarCollapsed={sidebarCollapsed}
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
