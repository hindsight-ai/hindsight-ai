import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes, Link, useLocation } from 'react-router-dom';
import MemoryBlockList from './components/MemoryBlockList';
import MemoryBlockDetail from './components/MemoryBlockDetail';
import KeywordManager from './components/KeywordManager';
import AgentManagementPage from './components/AgentManagementPage';
import ConsolidationSuggestions from './components/ConsolidationSuggestions';
import ConsolidationSuggestionDetail from './components/ConsolidationSuggestionDetail';
import ArchivedMemoryBlockList from './components/ArchivedMemoryBlockList';
import PruningSuggestions from './components/PruningSuggestions';
import AboutModal from './components/AboutModal';
import NotificationContainer from './components/NotificationContainer';
import authService from './api/authService';
import './App.css';

function AppContent() {
  const location = useLocation();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAboutModal, setShowAboutModal] = useState(false);

  useEffect(() => {
    fetchUserInfo();
  }, []);

  const fetchUserInfo = async () => {
    try {
      const userInfo = await authService.getCurrentUser();
      setUser(userInfo);
    } catch (error) {
      console.error('Error fetching user info:', error);
      // Ensure UI can render without crashing when auth/API fails
      setUser({ authenticated: false });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="App">
        <div className="loading-container">
          <div className="loading-spinner">Loading...</div>
        </div>
      </div>
    );
  }

  if (!user || !user.authenticated) {
    return (
      <div className="App">
        <header className="App-header">
          <h1 className="app-title">AI Agent Memory Dashboard</h1>
        </header>
        <main>
          <div className="auth-container">
            <h2>Authentication Required</h2>
            <p>Please sign in to access the AI Agent Memory Dashboard.</p>
            <button 
              className="auth-button" 
              onClick={() => window.location.href = 'https://auth.hindsight-ai.com/oauth2/sign_in?rd=https%3A%2F%2Fdashboard.hindsight-ai.com'}
            >
              Sign In
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="App">
      <NotificationContainer />
      <header className="App-header">
        <div className="header-content">
          <h1 className="app-title">AI Agent Memory Dashboard</h1>
          <div className="header-right">
            <div className="user-info">
              <span className="user-email">{(user && (user.email || user.user)) || 'Guest'}</span>
            </div>
            <button className="about-button" onClick={() => setShowAboutModal(true)}>
              About
            </button>
            {(location.pathname === '/' || location.pathname === '/memory-blocks') && (
              <Link to="/new-memory-block" className="add-button">
                + Add New Memory Block
              </Link>
            )}
          </div>
        </div>
        <div className="header-bottom">
          <nav className="main-nav">
            <ul className="nav-tabs">
              <li className="nav-item">
                <Link to="/" className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}>
                  Memory Blocks
                </Link>
              </li>
              <li className="nav-item">
                <Link to="/keywords" className={`nav-link ${location.pathname === '/keywords' ? 'active' : ''}`}>
                  Keywords
                </Link>
              </li>
              <li className="nav-item">
                <Link to="/agents" className={`nav-link ${location.pathname === '/agents' ? 'active' : ''}`}>
                  Agents
                </Link>
              </li>
              <li className="nav-item">
                <Link to="/consolidation-suggestions" className={`nav-link ${location.pathname === '/consolidation-suggestions' ? 'active' : ''}`}>
                  Consolidation Suggestions
                </Link>
              </li>
              <li className="nav-item">
                <Link to="/archived-memory-blocks" className={`nav-link ${location.pathname === '/archived-memory-blocks' ? 'active' : ''}`}>
                  Archived Memory Blocks
                </Link>
              </li>
              <li className="nav-item">
                <Link to="/pruning-suggestions" className={`nav-link ${location.pathname === '/pruning-suggestions' ? 'active' : ''}`}>
                  Memory Pruning
                </Link>
              </li>
            </ul>
          </nav>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<MemoryBlockList key={location.pathname} />} />
          <Route path="/memory-blocks" element={<MemoryBlockList key={location.pathname} />} />
          <Route path="/memory-blocks/:id" element={<MemoryBlockDetail />} />
          <Route path="/keywords" element={<KeywordManager />} />
          <Route path="/agents" element={<AgentManagementPage key={location.pathname} />} />
          <Route path="/consolidation-suggestions" element={<ConsolidationSuggestions key={location.pathname} />} />
          <Route path="/consolidation-suggestions/:id" element={<ConsolidationSuggestionDetail />} />
          <Route path="/archived-memory-blocks" element={<ArchivedMemoryBlockList key={location.pathname} />} />
          <Route path="/pruning-suggestions" element={<PruningSuggestions key={location.pathname} />} />
        </Routes>
      </main>
      <AboutModal isOpen={showAboutModal} onClose={() => setShowAboutModal(false)} />
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
