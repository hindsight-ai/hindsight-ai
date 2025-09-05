import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes, useLocation } from 'react-router-dom';

// Layout Components
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';

// Page Components
import MemoryBlocksPage from './components/MemoryBlocksPage';
import MemoryBlockDetail from './components/MemoryBlockDetail';
import KeywordManager from './components/KeywordManager';
import AgentManagementPage from './components/AgentManagementPage';
import AnalyticsPage from './components/AnalyticsPage';
import ConsolidationSuggestions from './components/ConsolidationSuggestions';
import ConsolidationSuggestionDetail from './components/ConsolidationSuggestionDetail';
import ArchivedMemoryBlockList from './components/ArchivedMemoryBlockList';
import PruningSuggestions from './components/PruningSuggestions';
import MemoryOptimizationCenter from './components/MemoryOptimizationCenter';
import AboutModal from './components/AboutModal';
import NotificationContainer from './components/NotificationContainer';
import { AuthProvider, useAuth } from './context/AuthContext';

function AppContent() {
  const location = useLocation();
  const { user, loading, guest, enterGuestMode } = useAuth();
  const [showAboutModal, setShowAboutModal] = useState(false);

  useEffect(() => {
    // Set document title
    document.title = 'Hindsight-AI';
  }, []);

  // Block UI until auth status known
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-gray-600">Loading…</div>
      </div>
    );
  }

  // Enforce authentication unless guest mode is enabled
  if (!guest && (!user || !user.authenticated))) {
    const handleSignIn = () => {
      const rd = encodeURIComponent(window.location.pathname + window.location.search + window.location.hash);
      window.location.href = `/oauth2/sign_in?rd=${rd}`;
    };
    const handleGuest = () => {
      enterGuestMode();
    };

    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-800 mb-4">AI Agent Memory Dashboard</h1>
          <div className="bg-white p-8 rounded-lg shadow-md max-w-md space-y-4">
            <h2 className="text-xl font-semibold">Authentication Required</h2>
            <p className="text-gray-600">Sign in to access your data, or explore a read-only guest tour.</p>
            <div className="flex gap-3 justify-center">
              <button
                className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg transition duration-200"
                onClick={handleSignIn}
              >
                Sign In
              </button>
              <button
                className="bg-gray-100 hover:bg-gray-200 text-gray-800 px-6 py-2 rounded-lg transition duration-200 border"
                onClick={handleGuest}
              >
                Explore as Guest
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Get page title based on current route
  const getPageTitle = (pathname) => {
    const routeMap = {
      '/': 'Dashboard',
      '/memory-blocks': 'Memory Blocks',
      '/keywords': 'Keywords',
      '/agents': 'Agents',
      '/analytics': 'Analytics',
      '/consolidation-suggestions': 'Consolidation',
      '/archived-memory-blocks': 'Archived',
      '/pruning-suggestions': 'Pruning'
    };

    // Handle dynamic routes
    if (pathname.startsWith('/memory-blocks/')) return 'Memory Block Detail';
    if (pathname.startsWith('/consolidation-suggestions/')) return 'Consolidation Detail';

    return routeMap[pathname] || 'Dashboard';
  };

  return (
    <div className="App" data-testid="dashboard-container">
      <NotificationContainer />

      <Layout title={getPageTitle(location.pathname)}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/memory-blocks" element={<MemoryBlocksPage key={location.pathname} />} />
          <Route path="/memory-blocks/:id" element={<MemoryBlockDetail />} />
          <Route path="/keywords" element={<KeywordManager />} />
          <Route path="/agents" element={<AgentManagementPage key={location.pathname} />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/consolidation-suggestions" element={<ConsolidationSuggestions key={location.pathname} />} />
          <Route path="/consolidation-suggestions/:id" element={<ConsolidationSuggestionDetail />} />
          <Route path="/archived-memory-blocks" element={<ArchivedMemoryBlockList key={location.pathname} />} />
          <Route path="/pruning-suggestions" element={<PruningSuggestions key={location.pathname} />} />
          <Route path="/memory-optimization-center" element={<MemoryOptimizationCenter />} />
        </Routes>
      </Layout>

      <AboutModal isOpen={showAboutModal} onClose={() => setShowAboutModal(false)} />
    </div>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
}

export default App;
