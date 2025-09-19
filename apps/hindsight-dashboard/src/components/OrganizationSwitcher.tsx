import React, { useState } from 'react';
import { useOrganization } from '../context/OrganizationContext';
import { CopyToClipboardButton } from './CopyToClipboardButton';
import notificationService from '../services/notificationService';

const OrganizationSwitcher: React.FC = () => {
  const {
    currentOrganization,
    userOrganizations,
    isPersonalMode,
    isPublicMode,
    loading,
    error,
    switchToPersonal,
    switchToOrganization,
    switchToPublic,
  } = useOrganization();
  
  const [isOpen, setIsOpen] = useState(false);

  const handleSwitch = (orgId: string | null) => {
    if (orgId === null) {
      switchToPersonal();
    } else {
      switchToOrganization(orgId);
    }
    setIsOpen(false);
  };

  const currentDisplayName = isPersonalMode ? 'Personal' : (isPublicMode ? 'Public' : currentOrganization?.name || 'Loading...');

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full md:min-w-[320px] md:max-w-[420px] px-3 py-2 text-left bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors duration-200"
        disabled={loading}
      >
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isPersonalMode ? 'bg-blue-500' : (isPublicMode ? 'bg-red-500' : 'bg-green-500')}`}></div>
          <span className="font-medium text-gray-900">
            {loading ? 'Loading...' : currentDisplayName}
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          ></div>
          <div className="absolute top-full left-0 right-0 md:right-auto mt-1 w-full md:w-[320px] bg-white border border-gray-200 rounded-lg shadow-lg z-20 max-h-80 overflow-y-auto">
            {error && (
              <div className="px-3 py-2 text-sm text-red-600 bg-red-50 border-b border-gray-200">
                {error}
              </div>
            )}
            
            <div className="py-1">
              {/* Personal option */}
              <button
                onClick={() => handleSwitch(null)}
                className={`w-full flex items-center px-3 py-2 text-left hover:bg-gray-50 transition-colors duration-200 ${
                  isPersonalMode ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                  <div>
                    <div className="font-medium">Personal</div>
                    <div className="text-xs text-gray-500">Your personal workspace</div>
                  </div>
                </div>
                {isPersonalMode && (
                  <svg className="w-4 h-4 ml-auto text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </button>

              {/* Organizations */}
              {userOrganizations.length > 0 && (
                <>
                  <div className="px-3 py-1 text-xs text-gray-500 bg-gray-50 border-t border-gray-200">
                    Organizations
                  </div>
                  {userOrganizations.map((org) => (
                    <button
                      key={org.id}
                      onClick={() => handleSwitch(org.id)}
                      className={`w-full flex items-center px-3 py-2 text-left hover:bg-gray-50 transition-colors duration-200 ${
                        currentOrganization?.id === org.id && !isPublicMode ? 'bg-green-50 text-green-700' : 'text-gray-700'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-2 h-2 rounded-full bg-green-500"></div>
                        <div>
                          <div className="font-medium">{org.name}</div>
                          <div className="text-xs text-gray-500">
                            {org.slug && `@${org.slug}`}
                            {!org.is_active && <span className="ml-1 text-orange-600">(Inactive)</span>}
                          </div>
                        </div>
                      </div>
                      <div className="ml-auto flex items-center gap-2">
                        {currentOrganization?.id === org.id && !isPublicMode && (
                          <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                        <span
                          role="button"
                          tabIndex={0}
                          onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(org.id); try { notificationService.showSuccess('Organization ID copied'); } catch {} }}
                          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); navigator.clipboard.writeText(org.id); try { notificationService.showSuccess('Organization ID copied'); } catch {} } }}
                          title="Copy Organization ID"
                          className="text-[10px] text-gray-500 border px-1 py-0.5 rounded hover:bg-gray-100"
                        >
                          Copy
                        </span>
                      </div>
                    </button>
                  ))}
                </>
              )}

              {userOrganizations.length === 0 && !loading && (
                <div className="px-3 py-2 text-sm text-gray-500 text-center border-t border-gray-200">
                  No organizations found
                </div>
              )}

              {/* Public option */}
              <div className="px-3 py-1 text-xs text-gray-500 bg-gray-50 border-t border-gray-200">
                Visibility
              </div>
              <button
                onClick={() => { switchToPublic(); setIsOpen(false); }}
                className={`w-full flex items-center px-3 py-2 text-left hover:bg-red-50 transition-colors duration-200 ${
                  isPublicMode ? 'bg-red-50 text-red-700' : 'text-gray-700'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 rounded-full bg-red-500"></div>
                  <div>
                    <div className="font-medium">Public</div>
                    <div className="text-xs text-gray-500">Everyone can see (read-only)</div>
                  </div>
                </div>
                {isPublicMode && (
                  <svg className="w-4 h-4 ml-auto text-red-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </>
      )}
      {/* Show Org ID with copy when an organization is active */}
      {!isPersonalMode && !isPublicMode && currentOrganization?.id && (
        <div className="mt-2 text-xs text-gray-500 flex items-center gap-2">
          <span>Org ID: {currentOrganization.id}</span>
          <CopyToClipboardButton textToCopy={currentOrganization.id} displayId="CopyOrgId" />
        </div>
      )}
    </div>
  );
};

export default OrganizationSwitcher;
