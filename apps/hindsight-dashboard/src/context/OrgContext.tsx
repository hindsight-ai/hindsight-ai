import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { useAuth } from './AuthContext';
import orgsService, { OrganizationSummary } from '../api/orgsService';

export type ScopeType = 'personal' | 'organization' | 'public';

interface OrgContextValue {
  organizations: OrganizationSummary[];
  activeScope: ScopeType;
  activeOrgId: string | null;
  setActiveScope: (scope: ScopeType) => void;
  setActiveOrgId: (orgId: string | null) => void;
  refreshOrgs: () => Promise<void>;
}

const OrgContext = createContext<OrgContextValue | undefined>(undefined);

export const OrgProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const { user, guest } = useAuth();
  const [organizations, setOrganizations] = useState<OrganizationSummary[]>([]);
  const [activeScope, setActiveScopeState] = useState<ScopeType>('personal');
  const [activeOrgId, setActiveOrgIdState] = useState<string | null>(null);

  useEffect(() => {
    try {
      const savedScope = sessionStorage.getItem('ACTIVE_SCOPE') as ScopeType | null;
      const savedOrg = sessionStorage.getItem('ACTIVE_ORG_ID');
      if (savedScope) setActiveScopeState(savedScope);
      if (savedOrg) setActiveOrgIdState(savedOrg);
    } catch {}
  }, []);

  const refreshOrgs = async () => {
    if (guest || !user?.authenticated) {
      setOrganizations([]);
      if (guest) setActiveScope('public');
      return;
    }
    try {
      const orgs = await orgsService.listOrganizations();
      setOrganizations(Array.isArray(orgs) ? orgs : []);
      if (activeScope === 'organization' && activeOrgId) {
        const stillThere = orgs.some(o => o.id === activeOrgId);
        if (!stillThere) {
          setActiveScope('personal');
          setActiveOrgId(null);
        }
      }
    } catch {
      setOrganizations([]);
    }
  };

  useEffect(() => { refreshOrgs(); }, [user?.authenticated, guest]);

  const setActiveScope = (scope: ScopeType) => {
    setActiveScopeState(scope);
    try { sessionStorage.setItem('ACTIVE_SCOPE', scope); } catch {}
  };
  const setActiveOrgId = (orgId: string | null) => {
    setActiveOrgIdState(orgId);
    try { if (orgId) sessionStorage.setItem('ACTIVE_ORG_ID', orgId); else sessionStorage.removeItem('ACTIVE_ORG_ID'); } catch {}
  };

  const value = useMemo<OrgContextValue>(() => ({ organizations, activeScope, activeOrgId, setActiveScope, setActiveOrgId, refreshOrgs }), [organizations, activeScope, activeOrgId]);

  return <OrgContext.Provider value={value}>{children}</OrgContext.Provider>;
};

export const useOrg = (): OrgContextValue => {
  const ctx = useContext(OrgContext);
  if (!ctx) throw new Error('useOrg must be used within OrgProvider');
  return ctx;
};
