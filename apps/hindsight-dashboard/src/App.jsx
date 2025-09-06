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
import LoginPage from './components/LoginPage';

function AppContent() {
  const location = useLocation();
  const { user, loading, guest, enterGuestMode, exitGuestMode } = useAuth();
  const [showAboutModal, setShowAboutModal] = useState(false);

  useEffect(() => {
    // Set document title
    document.title = 'Hindsight-AI';
  }, []);

  // Smooth scroll to top on route changes and after login/guest toggle
  useEffect(() => {
    try { window.scrollTo({ top: 0, left: 0, behavior: 'smooth' }); } catch { /* noop */ }
  }, [location.pathname, location.search, user?.authenticated, guest]);

  // Enforce authentication unless guest mode is enabled: auto-redirect to /login
  useEffect(() => {
    if (!loading && !guest && (!user || !user.authenticated) && location.pathname !== '/login') {
      try {
        window.history.replaceState(null, '', '/login');
      } catch {}
      window.location.replace('/login');
    }
  }, [loading, guest, user, location.pathname]);

  // If already authenticated and currently on /login, go to the main page
  useEffect(() => {
    if (!loading && user && user.authenticated && location.pathname === '/login') {
      try { window.location.replace('/dashboard'); } catch { window.location.href = '/dashboard'; }
    }
  }, [loading, user, location.pathname]);

  // Trampoline: if landing on '/', send to /dashboard (auth) or /login (unauth)
  useEffect(() => {
    if (!loading && location.pathname === '/') {
      if (user && user.authenticated) {
        try { window.location.replace('/dashboard'); } catch { window.location.href = '/dashboard'; }
      } else if (!guest) {
        try { window.location.replace('/login'); } catch { window.location.href = '/login'; }
      }
    }
  }, [loading, user, guest, location.pathname]);

  // Block UI until auth status known
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-start justify-center pt-8">
        <div className="text-gray-600">Loading…</div>
      </div>
    );
  }

  // Render a dedicated, full-screen login page without the dashboard layout
  if (location.pathname === '/login') {
    return <LoginPage />;
  }
  if (!guest && (!user || !user.authenticated) && location.pathname !== '/login') {
    return (
      <div className="min-h-screen bg-gray-100 flex items-start justify-center pt-8">
        <div className="text-gray-600">Redirecting to login…</div>
      </div>
    );
  }

  // Get page title based on current route
  const getPageTitle = (pathname) => {
    const routeMap = {
      '/dashboard': 'Dashboard',
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
          <Route path="/dashboard" element={<Dashboard />} />
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
