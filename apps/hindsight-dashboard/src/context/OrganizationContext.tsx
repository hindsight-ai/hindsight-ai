import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import organizationService, { Organization, OrganizationMember } from '../api/organizationService';
import { useAuth } from './AuthContext';

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
    try {
      sessionStorage.setItem('ACTIVE_SCOPE', 'personal');
      sessionStorage.removeItem('ACTIVE_ORG_ID');
    } catch {}
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
      try {
        sessionStorage.setItem('ACTIVE_SCOPE', 'organization');
        sessionStorage.setItem('ACTIVE_ORG_ID', orgId);
      } catch {}
      try { window.dispatchEvent(new Event('orgScopeChanged')); } catch {}
    } catch (err) {
      console.error('Failed to switch to organization:', err);
      setError(`Failed to switch to organization: ${err instanceof Error ? err.message : 'Unknown error'}`);
      switchToPersonal(); // Fallback to personal mode
    } finally {
      setLoading(false);
    }
  };

  // Load organizations when user authenticates and auth is not loading
  useEffect(() => {
    if (!authLoading && user?.authenticated) {
      refreshOrganizations();
    } else {
      // Clear everything when user logs out or auth is loading
      setCurrentOrganization(null);
      setUserOrganizations([]);
      setCurrentUserMembership(null);
      setIsPersonalMode(true);
      setIsPublicMode(false);
    }
  }, [user?.authenticated, authLoading]);

  const switchToPublic = () => {
    setCurrentOrganization(null);
    setCurrentUserMembership(null);
    setIsPersonalMode(false);
    setIsPublicMode(true);
    localStorage.removeItem('selectedOrganizationId');
    localStorage.setItem('selectedScope', 'public');
    try {
      sessionStorage.setItem('ACTIVE_SCOPE', 'public');
      sessionStorage.removeItem('ACTIVE_ORG_ID');
    } catch {}
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
