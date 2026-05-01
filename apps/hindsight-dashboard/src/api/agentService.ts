import { apiFetch, isGuest } from './http';
import { getScope } from './scopeProvider';

export interface Agent {
  agent_id: string;
  agent_name: string;
  visibility_scope?: 'personal' | 'organization' | 'public';
  organization_id?: string | null;
  owner_user_id?: string | null;
  created_at?: string;
  description?: string;
}

export interface PaginatedAgents {
  items: Agent[];
  total_items?: number;
}

const agentService = {
  getAgents: async (filters: Record<string, any> = {}): Promise<PaginatedAgents> => {
    const { per_page, ...rest } = filters;
    const params = new URLSearchParams({ ...rest, limit: per_page } as Record<string, string>);
    try {
      const { scope, orgId } = getScope();
      if (scope) params.set('scope', scope);
      if (scope === 'organization' && orgId) params.set('organization_id', orgId);
    } catch {}
    const response = await apiFetch('/agents/', { ensureTrailingSlash: true, searchParams: params });
    try {
      const data = await response.json();
      if (data && Array.isArray(data.items)) return data as PaginatedAgents;
      if (Array.isArray(data)) return { items: data } as PaginatedAgents;
      return { items: [] };
    } catch {
      return { items: [] };
    }
  },

  getAgentById: async (agentId: string): Promise<Agent> => {
    const response = await apiFetch(`/agents/${agentId}`);
    return response.json();
  },

  createAgent: async (data: Partial<Agent>, opts?: { scopeOverride?: { scope: 'personal' | 'organization' | 'public'; organizationId?: string | null } }): Promise<Agent> => {
    if (isGuest()) { throw new Error('Guest mode read-only'); }
    // Inject current org scope into create requests
    let payload: Partial<Agent> = { ...data };
    let searchParams: Record<string, any> | undefined = undefined;
    try {
      const overrideScope = opts?.scopeOverride?.scope;
      const overrideOrg = opts?.scopeOverride?.organizationId || undefined;
      const snapshot = getScope();
      const scope = overrideScope || snapshot.scope;
      const orgId = overrideScope ? (overrideScope === 'organization' ? (overrideOrg || undefined) : undefined) : snapshot.orgId;
      if (scope) {
        payload.visibility_scope = scope as any;
        // Also include as query params for backends that read scope from query on writes
        searchParams = { ...(searchParams || {}), scope };
      }
      if (scope === 'organization' && orgId) {
        payload.organization_id = orgId;
        searchParams = { ...(searchParams || {}), organization_id: orgId };
      }
    } catch {}

    const response = await apiFetch('/agents/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'include',
      // Ensure scope/org reach the API in environments that expect query-based scoping
      searchParams,
      ensureTrailingSlash: true,
    });
    return response.json();
  },

  deleteAgent: async (agentId: string): Promise<void> => {
    if (isGuest()) { throw new Error('Guest mode read-only'); }
    const response = await apiFetch(`/agents/${agentId}`, { method: 'DELETE' });
    if (response.status === 204) { return; }
    try { return await response.json(); } catch { return; }
  },

  updateAgent: async (agentId: string, data: Partial<Agent>): Promise<Agent> => {
    if (isGuest()) { throw new Error('Guest mode read-only'); }
    const response = await apiFetch(`/agents/${agentId}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data), credentials: 'include'
    });
    return response.json();
  },

  searchAgents: async (query: string): Promise<Agent[]> => {
    const params = new URLSearchParams({ query });
    try {
      const { scope, orgId } = getScope();
      if (scope) params.set('scope', scope);
      if (scope === 'organization' && orgId) params.set('organization_id', orgId);
    } catch {}
    const response = await apiFetch('/agents/search/', { ensureTrailingSlash: true, searchParams: params });
    return response.json();
  },
};

export default agentService;
