import notificationService from '../services/notificationService';

const isGuest = (): boolean => {
  try { return sessionStorage.getItem('GUEST_MODE') === 'true'; } catch { return false; }
};

let API_BASE_URL = '/api';
try {
  if (typeof window !== 'undefined' && (window as any).__ENV__?.HINDSIGHT_SERVICE_API_URL) {
    API_BASE_URL = (window as any).__ENV__.HINDSIGHT_SERVICE_API_URL;
  } else if (typeof process !== 'undefined' && process.env?.VITE_HINDSIGHT_SERVICE_API_URL) {
    API_BASE_URL = process.env.VITE_HINDSIGHT_SERVICE_API_URL;
  }
} catch {}

try {
  if (typeof window !== 'undefined' && API_BASE_URL) {
    const isHttps = window.location.protocol === 'https:';
    const url = new URL(API_BASE_URL, window.location.origin);
    if (isHttps && url.protocol === 'http:') {
      url.protocol = 'https:';
      API_BASE_URL = url.toString().replace(/\/$/, '');
    }
  }
} catch {}

const base = () => (isGuest() ? '/guest-api' : API_BASE_URL);

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
    const response = await fetch(`${base()}/agents/?${params.toString()}`, { credentials: 'include' });
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
    const response = await fetch(`${base()}/agents/${agentId}`, { credentials: 'include' });
    if (!response.ok) {
      if (response.status === 401) { notificationService.show401Error(); throw new Error('Authentication required'); }
      throw new Error(`HTTP error ${response.status}`);
    }
    return response.json();
  },

  createAgent: async (data: Partial<Agent>): Promise<Agent> => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to create agents.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/agents/`, {
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
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, { method: 'DELETE', credentials: 'include' });
    if (!response.ok && response.status !== 204) {
      if (response.status === 401) { notificationService.show401Error(); throw new Error('Authentication required'); }
      throw new Error(`HTTP error ${response.status}`);
    }
    if (response.status === 204) { return; }
  try { return await response.json(); } catch { return; }
  },

  updateAgent: async (agentId: string, data: Partial<Agent>): Promise<Agent> => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to update agents.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
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
    const response = await fetch(`${base()}/agents/search/?${params.toString()}`, { credentials: 'include' });
    if (!response.ok) {
      if (response.status === 401) { notificationService.show401Error(); throw new Error('Authentication required'); }
      throw new Error(`HTTP error ${response.status}`);
    }
    return response.json();
  },
};

export default agentService;
