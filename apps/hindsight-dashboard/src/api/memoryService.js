const API_BASE_URL = 'http://localhost:8000'; // Replace with your actual backend API URL

const memoryService = {
  // Memory Blocks
  getMemoryBlocks: async (filters = {}) => {
    const { per_page, ...rest } = filters;
    const params = new URLSearchParams({ ...rest, limit: per_page });
    const response = await fetch(`${API_BASE_URL}/memory-blocks/?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  getMemoryBlockById: async (id) => {
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${id}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  updateMemoryBlock: async (id, data) => {
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${id}`, {
      method: 'PUT',
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

  deleteMemoryBlock: async (id) => {
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    // For DELETE requests, a 204 No Content status means success with no body
    if (response.status === 204) {
      return; // No content to parse
    }
    return response.json();
  },

  // Keywords
  getKeywords: async () => {
    const response = await fetch(`${API_BASE_URL}/keywords`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  createKeyword: async (data) => {
    const response = await fetch(`${API_BASE_URL}/keywords`, {
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

  updateKeyword: async (id, data) => {
    const response = await fetch(`${API_BASE_URL}/keywords/${id}`, {
      method: 'PUT',
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

  deleteKeyword: async (id) => {
    const response = await fetch(`${API_BASE_URL}/keywords/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  // Memory Block Keywords Association
  addKeywordToMemoryBlock: async (memoryBlockId, keywordId) => {
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${memoryBlockId}/keywords/${keywordId}`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  removeKeywordFromMemoryBlock: async (memoryBlockId, keywordId) => {
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${memoryBlockId}/keywords/${keywordId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },
};

export default memoryService;
