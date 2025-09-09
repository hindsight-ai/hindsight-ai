import React, { useState, useEffect } from 'react';
import { getBuildInfo } from '../api/memoryService';

// Narrow env typing without redeclaring global ImportMeta
interface EnvVars { VITE_VERSION?: string; VITE_BUILD_SHA?: string; VITE_BUILD_TIMESTAMP?: string; VITE_DASHBOARD_IMAGE_TAG?: string; }

interface BuildInfo { service_name: string; version: string; build_sha: string; build_timestamp: string; image_tag: string; error?: string; }
interface AboutModalProps { isOpen: boolean; onClose: () => void; }

const AboutModal: React.FC<AboutModalProps> = ({ isOpen, onClose }) => {
  const [backendInfo, setBackendInfo] = useState<BuildInfo | null>(null);
  const [frontendInfo, setFrontendInfo] = useState<BuildInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { if (isOpen) { fetchBuildInfo(); } }, [isOpen]);

  const fetchBuildInfo = async () => {
    setLoading(true); setError(null);
    try { const backendData = await getBuildInfo(); setBackendInfo(backendData); }
    catch (err) { console.error('Error fetching backend build info:', err); setBackendInfo({ service_name: 'Hindsight Service', version: 'unknown', build_sha: 'unknown', build_timestamp: 'unknown', image_tag: 'unknown', error: 'Failed to fetch backend build information' }); }
    const env = (import.meta as any).env as EnvVars || {};
    const frontendData: BuildInfo = { service_name: 'AI Agent Memory Dashboard', version: env.VITE_VERSION || 'unknown', build_sha: env.VITE_BUILD_SHA || 'unknown', build_timestamp: env.VITE_BUILD_TIMESTAMP || 'unknown', image_tag: env.VITE_DASHBOARD_IMAGE_TAG || 'unknown' };
    setFrontendInfo(frontendData); setLoading(false);
  };

  if (!isOpen) return null;

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
        <div className="flex justify-end p-6 border-t border-gray-200">
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
