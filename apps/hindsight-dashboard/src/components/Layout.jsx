import React, { useState } from 'react';
import Sidebar from './Sidebar';
import MainContent from './MainContent'; // Ensure MainContent is used

const Layout = ({ children, title }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  const handleSidebarCollapse = (collapsed) => {
    setSidebarCollapsed(collapsed);
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={closeSidebar}
        onCollapseChange={handleSidebarCollapse}
      />

      {/* Main Content Area */}
      <MainContent
        title={title}
        toggleSidebar={toggleSidebar}
        sidebarCollapsed={sidebarCollapsed}
      >
        {children}
      </MainContent>
    </div>
  );
};

export default Layout;
