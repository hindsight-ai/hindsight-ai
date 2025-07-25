import React, { useState, useEffect } from 'react';
import { getBuildInfo } from '../api/memoryService';
import './AboutModal.css';

const AboutModal = ({ isOpen, onClose }) => {
  const [backendInfo, setBackendInfo] = useState(null);
  const [frontendInfo, setFrontendInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
      
      // Get frontend build information from environment variables
      const frontendData = {
        service_name: "AI Agent Memory Dashboard",
        version: process.env.REACT_APP_VERSION,
        build_sha: process.env.REACT_APP_BUILD_SHA,
        build_timestamp: process.env.REACT_APP_BUILD_TIMESTAMP,
        image_tag: process.env.REACT_APP_DASHBOARD_IMAGE_TAG
      };
      setFrontendInfo(frontendData);
    } catch (err) {
      console.error('Error fetching build info:', err);
      setError('Failed to load build information');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>About AI Agent Memory Dashboard</h2>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          {loading && <div className="loading">Loading build information...</div>}
          {error && <div className="error">{error}</div>}
          
          {backendInfo && (
            <div className="build-info-section">
              <h3>Backend Service</h3>
              <div className="build-info">
                <div className="info-item">
                  <label>Service:</label>
                  <span>{backendInfo.service_name || 'unknown'}</span>
                </div>
                <div className="info-item">
                  <label>Version:</label>
                  <span>{backendInfo.version || 'unknown'}</span>
                </div>
                <div className="info-item">
                  <label>Build SHA:</label>
                  <span className="mono">{backendInfo.build_sha || 'unknown'}</span>
                </div>
                <div className="info-item">
                  <label>Build Timestamp:</label>
                  <span>{backendInfo.build_timestamp || 'unknown'}</span>
                </div>
                <div className="info-item">
                  <label>Image Tag:</label>
                  <span className="mono">{backendInfo.image_tag || 'unknown'}</span>
                </div>
              </div>
            </div>
          )}
          
          {frontendInfo && (
            <div className="build-info-section">
              <h3>Frontend Dashboard</h3>
              <div className="build-info">
                <div className="info-item">
                  <label>Service:</label>
                  <span>{frontendInfo.service_name || 'unknown'}</span>
                </div>
                <div className="info-item">
                  <label>Version:</label>
                  <span>{frontendInfo.version || 'unknown'}</span>
                </div>
                <div className="info-item">
                  <label>Build SHA:</label>
                  <span className="mono">{frontendInfo.build_sha || 'unknown'}</span>
                </div>
                <div className="info-item">
                  <label>Build Timestamp:</label>
                  <span>{frontendInfo.build_timestamp || 'unknown'}</span>
                </div>
                <div className="info-item">
                  <label>Image Tag:</label>
                  <span className="mono">{frontendInfo.image_tag || 'unknown'}</span>
                </div>
              </div>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};

export default AboutModal;
