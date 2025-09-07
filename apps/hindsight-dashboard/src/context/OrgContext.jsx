import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { useAuth } from './AuthContext';
import orgsService from '../api/orgsService';

const OrgContext = createContext({
  organizations: [],
  activeScope: 'personal', // 'personal' | 'organization' | 'public'
  activeOrgId: null,
  setActiveScope: () => {},
  setActiveOrgId: () => {},
  refreshOrgs: async () => {},
});

export const OrgProvider = ({ children }) => {
  const { user, guest } = useAuth();
  const [organizations, setOrganizations] = useState([]);
  const [activeScope, setActiveScopeState] = useState('personal');
  const [activeOrgId, setActiveOrgIdState] = useState(null);

  // Load persisted selection
  useEffect(() => {
    try {
      const savedScope = sessionStorage.getItem('ACTIVE_SCOPE');
      const savedOrg = sessionStorage.getItem('ACTIVE_ORG_ID');
      if (savedScope) setActiveScopeState(savedScope);
      if (savedOrg) setActiveOrgIdState(savedOrg);
    } catch {}
  }, []);

  const refreshOrgs = async () => {
    if (guest || !user || !user.authenticated) {
      setOrganizations([]);
      // default to public in guest mode for clarity
      if (guest) {
        setActiveScope('public');
      }
      return;
    }
    try {
      const orgs = await orgsService.listOrganizations();
      setOrganizations(Array.isArray(orgs) ? orgs : []);
      // If current activeOrgId no longer present, reset
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

  const setActiveScope = (scope) => {
    setActiveScopeState(scope);
    try { sessionStorage.setItem('ACTIVE_SCOPE', scope); } catch {}
  };
  const setActiveOrgId = (orgId) => {
    setActiveOrgIdState(orgId);
    try { if (orgId) sessionStorage.setItem('ACTIVE_ORG_ID', orgId); else sessionStorage.removeItem('ACTIVE_ORG_ID'); } catch {}
  };

  const value = useMemo(() => ({
    organizations,
    activeScope,
    activeOrgId,
    setActiveScope,
    setActiveOrgId,
    refreshOrgs,
  }), [organizations, activeScope, activeOrgId]);

  return (
    <OrgContext.Provider value={value}>{children}</OrgContext.Provider>
  );
};

export const useOrg = () => useContext(OrgContext);

