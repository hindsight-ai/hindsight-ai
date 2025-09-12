import React, { useState, useEffect } from 'react';
import { getBuildInfo } from '../api/memoryService';
import memoryService from '../api/memoryService';
import notificationService from '../services/notificationService';
import { useAuth } from '../context/AuthContext';

interface BuildInfo {
  service_name: string;
  version: string;
  build_sha: string;
  build_timestamp: string;
  image_tag: string;
  error?: string;
}

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const AboutModal: React.FC<AboutModalProps> = ({ isOpen, onClose }) => {
  const [backendInfo, setBackendInfo] = useState<BuildInfo | null>(null);
  const [frontendInfo, setFrontendInfo] = useState<BuildInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState<boolean>(false);
  const [message, setMessage] = useState<string>('');
  const { user } = useAuth() as any;

  useEffect(() => {
    if (isOpen) {
      fetchBuildInfo();
    }
  }, [isOpen]);

  const fetchBuildInfo = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch backend build information
      const backendData = await getBuildInfo();
      setBackendInfo(backendData);
    } catch (err) {
      console.error('Error fetching backend build info:', err);
      setBackendInfo({
        service_name: "Hindsight Service",
        version: "unknown",
        build_sha: "unknown",
        build_timestamp: "unknown",
        image_tag: "unknown",
        error: "Failed to fetch backend build information"
      });
    }
    
    // Get frontend build information from environment variables
    const frontendData = {
      service_name: "AI Agent Memory Dashboard",
      version: import.meta.env.VITE_VERSION || "unknown",
      build_sha: import.meta.env.VITE_BUILD_SHA || "unknown",
      build_timestamp: import.meta.env.VITE_BUILD_TIMESTAMP || "unknown",
      image_tag: import.meta.env.VITE_DASHBOARD_IMAGE_TAG || "unknown"
    };
    setFrontendInfo(frontendData);
    
    setLoading(false);
  };

  if (!isOpen) return null;

  const handleContactSupport = async () => {
    if (sending) return;
    try {
      setSending(true);
      const payload: Record<string, any> = {
        message: message?.trim() || '',
        frontend: frontendInfo || {},
        context: {
          current_url: typeof window !== 'undefined' ? (window.location.href || '') : '',
          user_agent: typeof navigator !== 'undefined' ? (navigator.userAgent || '') : '',
          user_email: user?.email || null,
        },
      };
      await memoryService.contactSupport(payload);
      notificationService.showSuccess('Support request sent. Our team will reach out.');
    } catch (e: any) {
      notificationService.showError(e?.message || 'Failed to send support request');
    } finally {
      setSending(false);
    }
  };

  const buildMailtoHref = () => {
    const to = 'support@hindsight-ai.com';
    const f = frontendInfo || {} as any;
    const b = backendInfo || {} as any;
    const currentUrl = typeof window !== 'undefined' ? (window.location.href || '') : '';
    const ua = typeof navigator !== 'undefined' ? (navigator.userAgent || '') : '';
    const subject = `Hindsight AI Support – v${f.version || 'unknown'} (sha ${(f.build_sha || '').toString().slice(0,7) || 'unknown'})`;
    const bodyLines = [
      message?.trim() ? message.trim() : '(no message provided)',
      '',
      '--- Context ---',
      `User: ${user?.email || 'unknown'}`,
      `URL: ${currentUrl}`,
      `User Agent: ${ua}`,
      '',
      '--- Frontend ---',
      `Service: ${f.service_name || 'unknown'}`,
      `Version: ${f.version || 'unknown'}`,
      `Build SHA: ${f.build_sha || 'unknown'}`,
      `Build Timestamp: ${f.build_timestamp || 'unknown'}`,
      `Image Tag: ${f.image_tag || 'unknown'}`,
      '',
      '--- Backend ---',
      `Service: ${b.service_name || 'unknown'}`,
      `Version: ${b.version || 'unknown'}`,
      `Build SHA: ${b.build_sha || 'unknown'}`,
      `Build Timestamp: ${b.build_timestamp || 'unknown'}`,
      `Image Tag: ${b.image_tag || 'unknown'}`,
    ];
    const body = bodyLines.join('\n');
    return `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-800">About AI Agent Memory Dashboard</h2>
          <button
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
            onClick={onClose}
          >
            &times;
          </button>
        </div>
        <div className="p-6">
          {loading && (
            <div className="text-center py-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
              <p className="text-gray-600">Loading build information...</p>
            </div>
          )}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          {/* User message field */}
          <div className="mb-6">
            <h3 className="text-lg font-medium text-gray-800 mb-2">Describe your issue (optional)</h3>
            <textarea
              className="w-full border border-gray-300 rounded-md p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
              placeholder="Briefly describe the problem, steps to reproduce, and expected behavior."
              rows={4}
              maxLength={4000}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
            <div className="mt-1 text-xs text-gray-400">{message.length}/4000</div>
          </div>

          {backendInfo && (
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-800 mb-3">Backend Service</h3>
              {backendInfo.error && (
                <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded mb-4">
                  ⚠️ {backendInfo.error}
                </div>
              )}
              <div className="space-y-3">
                <div className="flex justify-between">
                  <label className="font-medium text-gray-600">Service:</label>
                  <span className="text-gray-800">{backendInfo.service_name || 'unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <label className="font-medium text-gray-600">Version:</label>
                  <span className="text-gray-800">{backendInfo.version || 'unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <label className="font-medium text-gray-600">Build SHA:</label>
                  <span className="font-mono text-sm text-gray-800">{backendInfo.build_sha || 'unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <label className="font-medium text-gray-600">Build Timestamp:</label>
                  <span className="text-gray-800">{backendInfo.build_timestamp || 'unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <label className="font-medium text-gray-600">Image Tag:</label>
                  <span className="font-mono text-sm text-gray-800">{backendInfo.image_tag || 'unknown'}</span>
                </div>
              </div>
            </div>
          )}

          {frontendInfo && (
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-800 mb-3">Frontend Dashboard</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <label className="font-medium text-gray-600">Service:</label>
                  <span className="text-gray-800">{frontendInfo.service_name || 'unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <label className="font-medium text-gray-600">Version:</label>
                  <span className="text-gray-800">{frontendInfo.version || 'unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <label className="font-medium text-gray-600">Build SHA:</label>
                  <span className="font-mono text-sm text-gray-800">{frontendInfo.build_sha || 'unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <label className="font-medium text-gray-600">Build Timestamp:</label>
                  <span className="text-gray-800">{frontendInfo.build_timestamp || 'unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <label className="font-medium text-gray-600">Image Tag:</label>
                  <span className="font-mono text-sm text-gray-800">{frontendInfo.image_tag || 'unknown'}</span>
                </div>
              </div>
            </div>
          )}
        </div>
        <div className="flex justify-between items-center p-6 border-t border-gray-200 gap-3 flex-wrap">
          <button
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition duration-200 disabled:opacity-60"
            onClick={handleContactSupport}
            disabled={sending}
            title="Send details to support@hindsight-ai.com"
          >
            {sending ? 'Sending…' : 'Contact Support'}
          </button>
          <a
            href={buildMailtoHref()}
            className="text-sm text-blue-600 hover:text-blue-800"
            title="Compose email using your mail app"
          >
            Open mail app instead
          </a>
          <button
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition duration-200"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default AboutModal;
