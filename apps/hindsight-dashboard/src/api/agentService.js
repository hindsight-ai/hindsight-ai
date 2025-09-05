import notificationService from '../services/notificationService';

const isGuest = () => {
  try { return sessionStorage.getItem('GUEST_MODE') === 'true'; } catch { return false; }
};

// Prefer relative proxy path to keep same-origin in all envs
let API_BASE_URL = import.meta.env.VITE_HINDSIGHT_SERVICE_API_URL || '/api';

// Upgrade API scheme at runtime to avoid mixed content when app is served over HTTPS
try {
  if (typeof window !== 'undefined' && API_BASE_URL) {
    const isHttps = window.location.protocol === 'https:';
    const url = new URL(API_BASE_URL, window.location.origin);
    if (isHttps && url.protocol === 'http:') {
      url.protocol = 'https:';
      // Normalize and drop trailing slash
      API_BASE_URL = url.toString().replace(/\/$/, '');
    }
  }
} catch (_) {
  // Ignore URL parsing errors and use the env value as-is
}

const base = () => (isGuest() ? '/guest-api' : API_BASE_URL);

const agentService = {
  // Agents
  getAgents: async (filters = {}) => {
    const { per_page, ...rest } = filters;
    const params = new URLSearchParams({ ...rest, limit: per_page });
    const response = await fetch(`${base()}/agents/?${params.toString()}`, {
      credentials: 'include'
    });
    if (!response.ok) {
      if (response.status === 401) {
        notificationService.show401Error();
        throw new Error('Authentication required');
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    try {
      const data = await response.json();
      // Ensure the response always has an 'items' array, even if empty
      if (data && Array.isArray(data.items)) {
        return data;
      } else if (Array.isArray(data)) {
        // If the API returns a raw array, wrap it in an object with 'items'
        return { items: data };
      }
      return { items: [] }; // Default to an empty items array
    } catch (jsonError) {
      console.error('Failed to parse JSON response for agents:', jsonError);
      return { items: [] }; // Return empty items on JSON parsing error
    }
  },

  getAgentById: async (agentId) => {
    const response = await fetch(`${base()}/agents/${agentId}`, {
      credentials: 'include'
    });
    if (!response.ok) {
      if (response.status === 401) {
        notificationService.show401Error();
        throw new Error('Authentication required');
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  createAgent: async (data) => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to create agents.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/agents/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
      credentials: 'include'
    });
    if (!response.ok) {
      if (response.status === 401) {
        notificationService.show401Error();
        throw new Error('Authentication required');
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  deleteAgent: async (agentId) => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to delete agents.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
      method: 'DELETE',
      credentials: 'include'
    });
    if (!response.ok) {
      if (response.status === 401) {
        notificationService.show401Error();
        throw new Error('Authentication required');
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    if (response.status === 204) {
      return;
    }
    return response.json();
  },

  updateAgent: async (agentId, data) => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to update agents.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
      credentials: 'include'
    });
    if (!response.ok) {
      if (response.status === 401) {
        notificationService.show401Error();
        throw new Error('Authentication required');
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  searchAgents: async (query) => {
    const params = new URLSearchParams({ query });
    const response = await fetch(`${base()}/agents/search/?${params.toString()}`, {
      credentials: 'include'
    });
    if (!response.ok) {
      if (response.status === 401) {
        notificationService.show401Error();
        throw new Error('Authentication required');
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },
};

export default agentService;
