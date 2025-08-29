import notificationService from '../services/notificationService';

const API_BASE_URL = process.env.REACT_APP_HINDSIGHT_SERVICE_API_URL;

if (!API_BASE_URL) {
  throw new Error("Environment variable REACT_APP_HINDSIGHT_SERVICE_API_URL is not defined.");
}

const agentService = {
  // Agents
  getAgents: async (filters = {}) => {
    const { per_page, ...rest } = filters;
    const params = new URLSearchParams({ ...rest, limit: per_page });
    const response = await fetch(`${API_BASE_URL}/agents/?${params.toString()}`, {
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

  createAgent: async (data) => {
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

  searchAgents: async (query) => {
    const params = new URLSearchParams({ query });
    const response = await fetch(`${API_BASE_URL}/agents/search/?${params.toString()}`, {
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
