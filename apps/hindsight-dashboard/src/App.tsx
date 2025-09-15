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
import SupportPage from './components/SupportPage';
import AboutModal from './components/AboutModal';
import NotificationContainer from './components/NotificationContainer';
import DebugPanel from './components/DebugPanel';
import { AuthProvider, useAuth } from './context/AuthContext';
import { OrgProvider } from './context/OrgContext';
import { OrganizationProvider } from './context/OrganizationContext';
import { NotificationProvider } from './context/NotificationContext';
import LoginPage from './components/LoginPage';
import ProfilePage from './components/ProfilePage';
import TokensPage from './components/TokensPage';
import organizationService from './api/organizationService';
import notificationService from './services/notificationService';

interface UserInfo {
  authenticated?: boolean;
}

function AppContent() {
  const location = useLocation();
  const { user, loading, guest } = useAuth() as any; // Will type AuthContext after migration
  const [showAboutModal, setShowAboutModal] = useState(false);
  const [showDebugPanel, setShowDebugPanel] = useState(false);

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
    const processInviteParams = async () => {
      const params = new URLSearchParams(location.search);
      const acceptId = params.get('accept_invite');
      const declineId = params.get('decline_invite');
      const org = params.get('org');
      const token = params.get('token') || undefined;
      if (org && (acceptId || declineId)) {
        try {
          if (acceptId) {
            await organizationService.acceptInvitation(org, acceptId, token);
            notificationService.showSuccess('Invitation accepted');
          } else if (declineId) {
            await organizationService.declineInvitation(org, declineId, token);
            notificationService.showInfo('Invitation declined');
          }
        } catch (e: any) {
          const msg = String(e?.message || '');
          if (msg.includes('HTTP error 400')) {
            notificationService.showWarning('This invitation link is no longer valid. Please request a new invite.');
          } else if (msg.includes('HTTP error 403')) {
            const emailParam = params.get('email');
            notificationService.showWarning(
              emailParam
                ? `This invitation is for ${emailParam}. Please sign in with that email or ask for a new invite.`
                : 'This invitation is for a different account. Please sign in with the invited email or request a new invite.'
            );
          } else if (msg.includes('HTTP error 404')) {
            notificationService.showWarning('Invitation not found. It may have been rescinded.');
          } else {
            notificationService.showError(`Failed to process invitation: ${msg || 'Unknown error'}`);
          }
        }
      }
      try { window.location.replace('/dashboard'); } catch { window.location.href = '/dashboard'; }
    };

    if (!loading && user && (user as UserInfo).authenticated && location.pathname === '/login') {
      // If login deep-link contains invite params, process them before redirecting.
      void processInviteParams();
    }
  }, [loading, user, location.pathname, location.search]);
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
      '/profile': 'Profile',
      '/memory-blocks': 'Memory Blocks',
      '/keywords': 'Keywords',
      '/agents': 'Agents',
      '/analytics': 'Analytics',
      '/consolidation-suggestions': 'Consolidation',
      '/archived-memory-blocks': 'Archived',
      '/pruning-suggestions': 'Pruning',
      '/support': 'Support'
    };
    if (pathname.startsWith('/memory-blocks/')) return 'Memory Block Detail';
    if (pathname.startsWith('/consolidation-suggestions/')) return 'Consolidation Detail';
    return routeMap[pathname] || 'Dashboard';
  };

  return (
    <div className="App" data-testid="dashboard-container">
      <NotificationContainer />
      <DebugPanel visible={showDebugPanel} />
      <Layout title={getPageTitle(location.pathname)} onOpenAbout={() => setShowAboutModal(true)} onToggleDebugPanel={() => setShowDebugPanel(prev => !prev)}>
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/tokens" element={<TokensPage />} />
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
          <Route path="/support" element={<SupportPage />} />
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
        <NotificationProvider>
          <OrganizationProvider>
            <OrgProvider>
              <AppContent />
            </OrgProvider>
          </OrganizationProvider>
        </NotificationProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
