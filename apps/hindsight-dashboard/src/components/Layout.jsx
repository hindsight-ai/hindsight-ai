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
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      {/* Fixed Sidebar */}
      <div className="fixed left-0 top-0 h-full z-10">
        <Sidebar
          isOpen={sidebarOpen}
          onClose={closeSidebar}
          onCollapseChange={handleSidebarCollapse}
        />
      </div>

  {/* Main Content Area - accounts for fixed sidebar width */}
  <div className={`flex-1 flex flex-col min-h-0 overflow-hidden ${sidebarCollapsed ? 'lg:ml-16 ml-0' : 'lg:ml-64 ml-0'}`}>
        <MainContent
          title={title}
          toggleSidebar={toggleSidebar}
          sidebarCollapsed={sidebarCollapsed}
        >
          {children}
        </MainContent>
      </div>
    </div>
  );
};

export default Layout;
