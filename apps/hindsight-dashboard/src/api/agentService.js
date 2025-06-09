const API_BASE_URL = 'http://localhost:8000'; // Replace with your actual backend API URL

const agentService = {
  // Agents
  getAgents: async (filters = {}) => {
    const { per_page, ...rest } = filters;
    const params = new URLSearchParams({ ...rest, limit: per_page });
    const response = await fetch(`${API_BASE_URL}/agents/?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  createAgent: async (data) => {
    const response = await fetch(`${API_BASE_URL}/agents/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  deleteAgent: async (agentId) => {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    if (response.status === 204) {
      return;
    }
    return response.json();
  },

  searchAgents: async (query) => {
    const params = new URLSearchParams({ query });
    const response = await fetch(`${API_BASE_URL}/agents/search/?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },
};

export default agentService;
