import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import organizationService, { Organization, OrganizationMember } from '../api/organizationService';
import { useAuth } from './AuthContext';
import { setScopeProvider } from '../api/scopeProvider';

interface OrganizationContextType {
  currentOrganization: Organization | null;
  userOrganizations: Organization[];
  currentUserMembership: OrganizationMember | null;
  isPersonalMode: boolean;
  isPublicMode: boolean;
  loading: boolean;
  error: string | null;
  switchToPersonal: () => void;
  switchToOrganization: (orgId: string) => void;
  switchToPublic: () => void;
  refreshOrganizations: () => Promise<void>;
}

const OrganizationContext = createContext<OrganizationContextType | undefined>(undefined);

export const useOrganization = () => {
  const context = useContext(OrganizationContext);
  if (context === undefined) {
    throw new Error('useOrganization must be used within an OrganizationProvider');
  }
  return context;
};

interface OrganizationProviderProps {
  children: ReactNode;
}

export const OrganizationProvider: React.FC<OrganizationProviderProps> = ({ children }) => {
  const { user, loading: authLoading } = useAuth();
  const [currentOrganization, setCurrentOrganization] = useState<Organization | null>(null);
  const [userOrganizations, setUserOrganizations] = useState<Organization[]>([]);
  const [currentUserMembership, setCurrentUserMembership] = useState<OrganizationMember | null>(null);
  const [isPersonalMode, setIsPersonalMode] = useState(true);
  const [isPublicMode, setIsPublicMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load user's organizations when authenticated
  const refreshOrganizations = async () => {
    if (!user?.authenticated) return;

    try {
      setLoading(true);
      setError(null);
      const organizations = await organizationService.getOrganizations();
      setUserOrganizations(organizations);
      
      // Restore scope preference
      const savedScope = localStorage.getItem('selectedScope');
      const savedOrgId = localStorage.getItem('selectedOrganizationId');
      if (savedScope === 'public') {
        switchToPublic();
      } else if (savedOrgId && organizations.find(org => org.id === savedOrgId)) {
        await switchToOrganization(savedOrgId);
      } else {
        switchToPersonal();
      }
    } catch (err) {
      console.error('Failed to load organizations:', err);
      setError('Failed to load organizations');
      switchToPersonal(); // Fallback to personal mode
    } finally {
      setLoading(false);
    }
  };

  const switchToPersonal = () => {
    setCurrentOrganization(null);
    setCurrentUserMembership(null);
    setIsPersonalMode(true);
    setIsPublicMode(false);
    localStorage.removeItem('selectedOrganizationId');
    localStorage.setItem('selectedScope', 'personal');
    try { window.dispatchEvent(new Event('orgScopeChanged')); } catch {}
  };

  const switchToOrganization = async (orgId: string) => {
    try {
      setLoading(true);
      setError(null);
      
      // Get organization details and current user's membership
      const [organization, members] = await Promise.all([
        organizationService.getOrganization(orgId),
        organizationService.getMembers(orgId)
      ]);
      
      // Find current user's membership or allow superadmins
      const membership = members.find(member => member.email === user?.email);
      if (!membership && !user?.is_superadmin) {
        throw new Error('You are not a member of this organization');
      }
      
      setCurrentOrganization(organization);
      setCurrentUserMembership(membership);
      setIsPersonalMode(false);
      setIsPublicMode(false);
      localStorage.setItem('selectedOrganizationId', orgId);
      localStorage.setItem('selectedScope', 'organization');
      try { window.dispatchEvent(new Event('orgScopeChanged')); } catch {}
    } catch (err) {
      console.error('Failed to switch to organization:', err);
      setError(`Failed to switch to organization: ${err instanceof Error ? err.message : 'Unknown error'}`);
      switchToPersonal(); // Fallback to personal mode
    } finally {
      setLoading(false);
    }
  };

  // Track previous user email so we can detect user swaps (auth swap without
  // an explicit logout, e.g. dev-mode header change). Surfaced by failure-mode
  // analysis: without this the previous user's localStorage scope leaks into
  // the next user's session.
  const previousUserEmailRef = useRef<string | undefined>(undefined);

  // Load organizations when user authenticates and auth is not loading.
  // Also clear persisted scope on logout OR user-swap to avoid scope leak
  // between users.
  useEffect(() => {
    const previousEmail = previousUserEmailRef.current;
    const currentEmail = user?.email;
    const userSwapped = previousEmail !== undefined && currentEmail !== undefined && previousEmail !== currentEmail;
    previousUserEmailRef.current = currentEmail;

    if (userSwapped) {
      try {
        localStorage.removeItem('selectedScope');
        localStorage.removeItem('selectedOrganizationId');
      } catch {}
    }

    if (!authLoading && user?.authenticated) {
      refreshOrganizations();
    } else {
      // Clear React state when user logs out OR while auth is still loading.
      setCurrentOrganization(null);
      setUserOrganizations([]);
      setCurrentUserMembership(null);
      setIsPersonalMode(true);
      setIsPublicMode(false);
      // Only clear persisted scope on a DEFINITIVE logout (auth resolved AND
      // user is unauthenticated). On the very first mount, `authLoading=true`
      // and `user=null` — entering this branch and wiping localStorage at that
      // moment destroys any preference the user (or an init script in tests)
      // just wrote. Wait for auth to settle before deciding.
      if (!authLoading) {
        try {
          localStorage.removeItem('selectedScope');
          localStorage.removeItem('selectedOrganizationId');
        } catch {}
      }
    }
  }, [user?.authenticated, user?.email, authLoading]);

  // Wire the scope provider so HTTP services can read live scope without
  // touching storage directly. Fires on every scope-affecting state change.
  useEffect(() => {
    setScopeProvider(() => ({
      scope: isPublicMode ? 'public' : isPersonalMode ? 'personal' : 'organization',
      orgId: currentOrganization?.id ?? undefined,
    }));
  }, [isPublicMode, isPersonalMode, currentOrganization?.id]);

  const switchToPublic = () => {
    setCurrentOrganization(null);
    setCurrentUserMembership(null);
    setIsPersonalMode(false);
    setIsPublicMode(true);
    localStorage.removeItem('selectedOrganizationId');
    localStorage.setItem('selectedScope', 'public');
    try { window.dispatchEvent(new Event('orgScopeChanged')); } catch {}
  };

  const value: OrganizationContextType = {
    currentOrganization,
    userOrganizations,
    currentUserMembership,
    isPersonalMode,
    isPublicMode,
    loading,
    error,
    switchToPersonal,
    switchToOrganization,
    switchToPublic,
    refreshOrganizations,
  };

  return (
    <OrganizationContext.Provider value={value}>
      {children}
    </OrganizationContext.Provider>
  );
};
