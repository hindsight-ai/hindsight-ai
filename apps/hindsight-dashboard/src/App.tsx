import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes, useLocation } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
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
import { OrgProvider } from './context/OrgContext';
import { OrganizationProvider } from './context/OrganizationContext';
import LoginPage from './components/LoginPage';

interface UserInfo {
  authenticated?: boolean;
}

function AppContent() {
  const location = useLocation();
  const { user, loading, guest } = useAuth() as any; // Will type AuthContext after migration
  const [showAboutModal, setShowAboutModal] = useState(false);

  useEffect(() => { document.title = 'Hindsight-AI'; }, []);
  useEffect(() => { try { window.scrollTo({ top: 0, left: 0, behavior: 'smooth' }); } catch {} }, [location.pathname, location.search, (user as UserInfo)?.authenticated, guest]);
  useEffect(() => {
    const isOAuthPath = location.pathname.startsWith('/oauth2');
    if (!loading && !guest && !isOAuthPath && (!user || !(user as UserInfo).authenticated) && location.pathname !== '/login') {
      try { window.history.replaceState(null, '', '/login'); } catch {}
      window.location.replace('/login');
    }
  }, [loading, guest, user, location.pathname]);
  useEffect(() => {
    if (!loading && user && (user as UserInfo).authenticated && location.pathname === '/login') {
      try { window.location.replace('/dashboard'); } catch { window.location.href = '/dashboard'; }
    }
  }, [loading, user, location.pathname]);
  useEffect(() => {
    if (!loading && location.pathname === '/') {
      if (user && (user as UserInfo).authenticated) {
        try { window.location.replace('/dashboard'); } catch { window.location.href = '/dashboard'; }
      } else if (!guest) {
        try { window.location.replace('/login'); } catch { window.location.href = '/login'; }
      }
    }
  }, [loading, user, guest, location.pathname]);

  if (loading) {
    return (<div className="min-h-screen bg-gray-100 flex items-start justify-center pt-8"><div className="text-gray-600">Loading…</div></div>);
  }
  if (location.pathname === '/login') return <LoginPage />;
  if (!guest && (!user || !(user as UserInfo).authenticated) && location.pathname !== '/login') {
    return (<div className="min-h-screen bg-gray-100 flex items-start justify-center pt-8"><div className="text-gray-600">Redirecting to login…</div></div>);
  }

  const getPageTitle = (pathname: string): string => {
    const routeMap: Record<string, string> = {
      '/dashboard': 'Dashboard',
      '/memory-blocks': 'Memory Blocks',
      '/keywords': 'Keywords',
      '/agents': 'Agents',
      '/analytics': 'Analytics',
      '/consolidation-suggestions': 'Consolidation',
      '/archived-memory-blocks': 'Archived',
      '/pruning-suggestions': 'Pruning'
    };
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
        <OrganizationProvider>
          <OrgProvider>
            <AppContent />
          </OrgProvider>
        </OrganizationProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
