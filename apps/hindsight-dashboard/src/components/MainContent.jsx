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
          <button className="p-2 rounded-full hover:bg-gray-200 transition duration-200">
            <svg className="w-6 h-6 text-gray-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </button>
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
