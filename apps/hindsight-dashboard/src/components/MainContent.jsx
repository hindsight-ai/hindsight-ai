import React from 'react';
import UserAccountButton from './UserAccountButton';
import { useAuth } from '../context/AuthContext';

const MainContent = ({ children, title, sidebarCollapsed }) => {
  const { guest } = useAuth();
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
        <div className="flex items-center gap-3">
          {guest && (
            <span className="px-3 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 border border-yellow-200">
              Guest Mode · Read-only
            </span>
          )}
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
