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
import FloatingActionButton from './components/FloatingActionButton';
import ThemeToggle from './components/ThemeToggle';

import authService from './api/authService';
import './App.css';

function AppContent() {
  const location = useLocation();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAboutModal, setShowAboutModal] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);


  useEffect(() => {
    fetchUserInfo();
    // Set document title
    document.title = 'Hindsight-AI';
  }, []);

  const fetchUserInfo = async () => {
    try {
      const userInfo = await authService.getCurrentUser();
      setUser(userInfo);
    } catch (error) {
      console.error('Error fetching user info:', error);
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

  // if (!user || !user.authenticated) {
  //   return (
  //     <div className="App">
  //       <header className="App-header">
  //         <h1 className="app-title">AI Agent Memory Dashboard</h1>
  //       </header>
  //       <main>
  //         <div className="auth-container">
  //           <h2>Authentication Required</h2>
  //           <p>Please sign in to access the AI Agent Memory Dashboard.</p>
  //           <button 
  //             className="auth-button" 
  //             onClick={() => window.location.href = 'https://auth.hindsight-ai.com/oauth2/sign_in?rd=https%3A%2F%2Fdashboard.hindsight-ai.com'}
  //           >
  //             Sign In
  //           </button>
  //         </div>
  //       </main>
  //     </div>
  //   );
  // }

  return (
    <div className="App" data-testid="dashboard-container">
      <NotificationContainer />
      <header className="App-header fixed-header" role="banner">
        <div className="header-content">
          {/* Navigation Tabs - Now in the same row */}
          <nav className="main-nav inline-nav" data-testid="main-nav" role="navigation" aria-label="Main navigation">
            <ul className="nav-tabs">
              <li className="nav-item">
                <Link
                  to="/"
                  className={`nav-link ${location.pathname === '/' || location.pathname === '/memory-blocks' ? 'active' : ''}`}
                  data-testid="nav-dashboard"
                >
                  Memory Blocks
                </Link>
              </li>
              <li className="nav-item">
                <Link
                  to="/keywords"
                  className={`nav-link ${location.pathname === '/keywords' ? 'active' : ''}`}
                  data-testid="nav-keywords"
                >
                  Keywords
                </Link>
              </li>
              <li className="nav-item">
                <Link
                  to="/agents"
                  className={`nav-link ${location.pathname === '/agents' ? 'active' : ''}`}
                  data-testid="nav-agents"
                >
                  Agents
                </Link>
              </li>
              <li className="nav-item">
                <Link
                  to="/consolidation-suggestions"
                  className={`nav-link ${location.pathname === '/consolidation-suggestions' ? 'active' : ''}`}
                  data-testid="nav-consolidation"
                >
                  Consolidation
                </Link>
              </li>
              <li className="nav-item">
                <Link
                  to="/archived-memory-blocks"
                  className={`nav-link ${location.pathname === '/archived-memory-blocks' ? 'active' : ''}`}
                  data-testid="nav-archived"
                >
                  Archived
                </Link>
              </li>
              <li className="nav-item">
                <Link
                  to="/pruning-suggestions"
                  className={`nav-link ${location.pathname === '/pruning-suggestions' ? 'active' : ''}`}
                  data-testid="nav-pruning"
                >
                  Pruning
                </Link>
              </li>
            </ul>
          </nav>

          <div className="header-right">
            <ThemeToggle />
            <div className="user-info">
              <span className="user-email">{user.email || user.user}</span>
            </div>
            <button
              className="about-button"
              onClick={() => setShowAboutModal(true)}
              aria-label="About this application"
            >
              About
            </button>

          </div>
        </div>

        {/* Mobile Menu Toggle - Now positioned differently */}
        <button
          className="mobile-menu-toggle"
          data-testid="mobile-menu-toggle"
          aria-label="Toggle mobile menu"
          onClick={() => setShowMobileMenu(!showMobileMenu)}
        >
          ☰
        </button>
      </header>
      <main role="main" data-testid="main-content">
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

      {/* Mobile Navigation Menu */}
      <div
        className={`mobile-nav-menu ${showMobileMenu ? 'show' : ''}`}
        data-testid="mobile-nav-menu"
      >
        <nav role="navigation" aria-label="Mobile navigation">
          <ul>
            <li><Link to="/" data-testid="mobile-nav-dashboard" onClick={() => setShowMobileMenu(false)}>Memory Blocks</Link></li>
            <li><Link to="/keywords" data-testid="mobile-nav-keywords" onClick={() => setShowMobileMenu(false)}>Keywords</Link></li>
            <li><Link to="/agents" data-testid="mobile-nav-agents" onClick={() => setShowMobileMenu(false)}>Agents</Link></li>
            <li><Link to="/consolidation-suggestions" data-testid="mobile-nav-consolidation" onClick={() => setShowMobileMenu(false)}>Consolidation</Link></li>
            <li><Link to="/archived-memory-blocks" data-testid="mobile-nav-archived" onClick={() => setShowMobileMenu(false)}>Archived</Link></li>
            <li><Link to="/pruning-suggestions" data-testid="mobile-nav-pruning" onClick={() => setShowMobileMenu(false)}>Pruning</Link></li>
          </ul>
        </nav>
      </div>

      {/* Floating Action Button */}
      {(location.pathname === '/' || location.pathname === '/memory-blocks') && (
        <FloatingActionButton onMemoryBlockAdded={() => {
          // This will trigger a refresh of the memory blocks list
          // The MemoryBlockList component will handle the refresh
          window.dispatchEvent(new CustomEvent('memoryBlockAdded'));
        }} />
      )}



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
