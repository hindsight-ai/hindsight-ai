import notificationService from '../services/notificationService';
import { apiFetch, isGuest, apiUrl } from './http';

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
      const scope = sessionStorage.getItem('ACTIVE_SCOPE');
      const orgId = sessionStorage.getItem('ACTIVE_ORG_ID');
      if (scope) params.set('scope', scope);
      if (scope === 'organization' && orgId) params.set('organization_id', orgId);
    } catch {}
    const response = await apiFetch('/agents/', { ensureTrailingSlash: true, searchParams: params });
    if (!response.ok) {
      if (response.status === 401) { notificationService.show401Error(); throw new Error('Authentication required'); }
      throw new Error(`HTTP error ${response.status}`);
    }
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
    if (!response.ok) {
      if (response.status === 401) { notificationService.show401Error(); throw new Error('Authentication required'); }
      throw new Error(`HTTP error ${response.status}`);
    }
    return response.json();
  },

  createAgent: async (data: Partial<Agent>): Promise<Agent> => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to create agents.'); throw new Error('Guest mode read-only'); }
    const response = await apiFetch('/agents/', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data), credentials: 'include'
    });
    if (!response.ok) {
      if (response.status === 401) { notificationService.show401Error(); throw new Error('Authentication required'); }
  throw new Error(`HTTP error ${response.status}`);
    }
    return response.json();
  },

  deleteAgent: async (agentId: string): Promise<void> => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to delete agents.'); throw new Error('Guest mode read-only'); }
    const response = await apiFetch(`/agents/${agentId}`, { method: 'DELETE' });
    if (!response.ok && response.status !== 204) {
      if (response.status === 401) { notificationService.show401Error(); throw new Error('Authentication required'); }
      throw new Error(`HTTP error ${response.status}`);
    }
    if (response.status === 204) { return; }
  try { return await response.json(); } catch { return; }
  },

  updateAgent: async (agentId: string, data: Partial<Agent>): Promise<Agent> => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to update agents.'); throw new Error('Guest mode read-only'); }
    const response = await apiFetch(`/agents/${agentId}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data), credentials: 'include'
    });
    if (!response.ok) {
      if (response.status === 401) { notificationService.show401Error(); throw new Error('Authentication required'); }
      throw new Error(`HTTP error ${response.status}`);
    }
    return response.json();
  },

  searchAgents: async (query: string): Promise<Agent[]> => {
    const params = new URLSearchParams({ query });
    try {
      const scope = sessionStorage.getItem('ACTIVE_SCOPE');
      const orgId = sessionStorage.getItem('ACTIVE_ORG_ID');
      if (scope) params.set('scope', scope);
      if (scope === 'organization' && orgId) params.set('organization_id', orgId);
    } catch {}
    const response = await apiFetch('/agents/search/', { ensureTrailingSlash: true, searchParams: params });
    if (!response.ok) {
      if (response.status === 401) { notificationService.show401Error(); throw new Error('Authentication required'); }
      throw new Error(`HTTP error ${response.status}`);
    }
    return response.json();
  },
};

export default agentService;
