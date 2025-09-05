import React from 'react';
import UserAccountButton from './UserAccountButton';

const MainContent = ({ children, title, sidebarCollapsed }) => {
  return (
    <main className={`flex-1 flex flex-col overflow-y-auto transition-all duration-300 ease-in-out ${
      sidebarCollapsed ? 'lg:p-4' : 'lg:p-4'
    }`}>
      {/* Content Header - Matching target design exactly */}
      <header className="p-4 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">{title}</h2>
          <p className="text-gray-500">
            {title === 'Dashboard'
              ? 'Overview of your AI memory management system'
              : `Manage your ${title.toLowerCase()}`
            }
          </p>
        </div>
        <div>
          <UserAccountButton />
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 p-4">
        {children}
      </div>


    </main>
  );
};

export default MainContent;
