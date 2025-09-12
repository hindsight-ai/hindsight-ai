/**
 * Notification Settings Modal Component
 * 
 * Modal for managing notification preferences including email and in-app settings.
 * Allows users to control which events trigger notifications.
 */

import React, { useState, useEffect } from 'react';
import { useNotifications } from '../context/NotificationContext';
import { useAuth } from '../context/AuthContext';
import useModal from '../hooks/useModal';

interface NotificationSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface EventTypeConfig {
  key: string;
  label: string;
  description: string;
  category: 'organization' | 'system';
}

const EVENT_TYPES: EventTypeConfig[] = [
  {
    key: 'org_invitation',
    label: 'Organization Invitations',
    description: 'When you are invited to join an organization',
    category: 'organization'
  },
  {
    key: 'org_membership_added',
    label: 'Added to Organization',
    description: 'When you are added to an organization',
    category: 'organization'
  },
  {
    key: 'org_membership_removed',
    label: 'Removed from Organization',
    description: 'When you are removed from an organization',
    category: 'organization'
  },
  {
    key: 'org_role_changed',
    label: 'Role Changes',
    description: 'When your role in an organization changes',
    category: 'organization'
  },
  {
    key: 'org_invitation_accepted',
    label: 'Invitation Accepted',
    description: 'When someone accepts your organization invitation',
    category: 'organization'
  },
  {
    key: 'org_invitation_declined',
    label: 'Invitation Declined',
    description: 'When someone declines your organization invitation',
    category: 'organization'
  }
];

const NotificationSettingsModal: React.FC<NotificationSettingsModalProps> = ({ isOpen, onClose }) => {
  const { preferences, preferencesLoading, updatePreference } = useNotifications();
  const { guest } = useAuth();
  const { handleBackdropClick, backdropClasses } = useModal();
  
  const [saving, setSaving] = useState<string | null>(null); // Track which preference is being saved
  const [saveStatus, setSaveStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null);

  // Clear save status after a delay
  useEffect(() => {
    if (saveStatus) {
      const timer = setTimeout(() => setSaveStatus(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [saveStatus]);

  const handlePreferenceChange = async (
    eventType: string,
    field: 'email_enabled' | 'in_app_enabled',
    value: boolean
  ) => {
    if (guest || !preferences) return;

    try {
      setSaving(`${eventType}-${field}`);
      
      const currentPrefs = preferences[eventType];
      const updateData = field === 'email_enabled' 
        ? { emailEnabled: value, inAppEnabled: currentPrefs?.in_app_enabled }
        : { emailEnabled: currentPrefs?.email_enabled, inAppEnabled: value };

      await updatePreference(eventType, updateData.emailEnabled, updateData.inAppEnabled);
      
      setSaveStatus({ type: 'success', message: 'Preference updated successfully' });
    } catch (error) {
      console.error('Failed to update preference:', error);
      setSaveStatus({ type: 'error', message: 'Failed to update preference' });
    } finally {
      setSaving(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className={backdropClasses} onClick={handleBackdropClick}>
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Notification Settings</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close modal"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* Guest User Message */}
          {guest && (
            <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-center">
                <svg className="w-5 h-5 text-yellow-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-yellow-800">Guest Mode</p>
                  <p className="text-sm text-yellow-700">Notification settings are not available in guest mode.</p>
                </div>
              </div>
            </div>
          )}

          {/* Loading State */}
          {preferencesLoading && !guest && (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-sm text-gray-500 mt-2">Loading preferences...</p>
            </div>
          )}

          {/* Preferences Content */}
          {!preferencesLoading && !guest && preferences && (
            <div className="space-y-6">
              {/* Save Status */}
              {saveStatus && (
                <div className={`p-3 rounded-lg ${
                  saveStatus.type === 'success' 
                    ? 'bg-green-50 border border-green-200 text-green-800' 
                    : 'bg-red-50 border border-red-200 text-red-800'
                }`}>
                  <p className="text-sm font-medium">{saveStatus.message}</p>
                </div>
              )}

              {/* Introduction */}
              <div>
                <p className="text-sm text-gray-600">
                  Choose how you want to be notified about different events. You can control both email and in-app notifications separately.
                </p>
              </div>

              {/* Organization Events */}
              <div>
                <h3 className="text-base font-medium text-gray-900 mb-4">Organization Events</h3>
                <div className="space-y-4">
                  {EVENT_TYPES.filter(event => event.category === 'organization').map((eventType) => {
                    const prefs = preferences[eventType.key] || { email_enabled: true, in_app_enabled: true };
                    
                    return (
                      <div key={eventType.key} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="text-sm font-medium text-gray-900">{eventType.label}</h4>
                            <p className="text-sm text-gray-500 mt-1">{eventType.description}</p>
                          </div>
                          
                          <div className="ml-4 flex items-center gap-6">
                            {/* Email Toggle */}
                            <div className="flex items-center gap-2">
                              <label className="text-xs text-gray-600">Email</label>
                              <button
                                onClick={() => handlePreferenceChange(eventType.key, 'email_enabled', !prefs.email_enabled)}
                                disabled={saving === `${eventType.key}-email_enabled`}
                                className={`
                                  relative inline-flex h-5 w-9 rounded-full transition-colors duration-200 ease-in-out
                                  ${prefs.email_enabled ? 'bg-blue-600' : 'bg-gray-300'}
                                  ${saving === `${eventType.key}-email_enabled` ? 'opacity-50' : ''}
                                `}
                              >
                                <span
                                  className={`
                                    inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform duration-200 ease-in-out mt-0.5
                                    ${prefs.email_enabled ? 'translate-x-4' : 'translate-x-0.5'}
                                  `}
                                />
                              </button>
                              {saving === `${eventType.key}-email_enabled` && (
                                <div className="w-3 h-3 border border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                              )}
                            </div>
                            
                            {/* In-App Toggle */}
                            <div className="flex items-center gap-2">
                              <label className="text-xs text-gray-600">In-App</label>
                              <button
                                onClick={() => handlePreferenceChange(eventType.key, 'in_app_enabled', !prefs.in_app_enabled)}
                                disabled={saving === `${eventType.key}-in_app_enabled`}
                                className={`
                                  relative inline-flex h-5 w-9 rounded-full transition-colors duration-200 ease-in-out
                                  ${prefs.in_app_enabled ? 'bg-blue-600' : 'bg-gray-300'}
                                  ${saving === `${eventType.key}-in_app_enabled` ? 'opacity-50' : ''}
                                `}
                              >
                                <span
                                  className={`
                                    inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform duration-200 ease-in-out mt-0.5
                                    ${prefs.in_app_enabled ? 'translate-x-4' : 'translate-x-0.5'}
                                  `}
                                />
                              </button>
                              {saving === `${eventType.key}-in_app_enabled` && (
                                <div className="w-3 h-3 border border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Footer Info */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-900 mb-2">About Notifications</h4>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• <strong>Email notifications</strong> are sent to your registered email address</li>
                  <li>• <strong>In-app notifications</strong> appear in the notification bell when you're logged in</li>
                  <li>• Changes are saved automatically</li>
                  <li>• You can always change these settings later</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotificationSettingsModal;
