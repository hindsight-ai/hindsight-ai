import notificationService from '../services/notificationService';

const API_BASE_URL = process.env.REACT_APP_HINDSIGHT_SERVICE_API_URL;

if (!API_BASE_URL) {
  throw new Error("Environment variable REACT_APP_HINDSIGHT_SERVICE_API_URL is not defined.");
}

const memoryService = {
  // Memory Blocks
  getMemoryBlocks: async (filters = {}) => {
    const { per_page, include_archived = false, ...rest } = filters; // Destructure include_archived with default false
    const params = new URLSearchParams({ ...rest, limit: per_page, include_archived }); // Pass it to params
    const response = await fetch(`${API_BASE_URL}/memory-blocks/?${params.toString()}`, {
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

  getMemoryBlockById: async (id) => {
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${id}`, {
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

  updateMemoryBlock: async (id, data) => {
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${id}`, {
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

  archiveMemoryBlock: async (id) => {
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${id}/archive`, {
      method: 'POST',
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

  deleteMemoryBlock: async (id) => {
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${id}/hard-delete`, { // Assuming a new hard-delete endpoint
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

  getArchivedMemoryBlocks: async (filters = {}) => {
    const { per_page, ...rest } = filters;
    const params = new URLSearchParams({ ...rest, limit: per_page });
    const response = await fetch(`${API_BASE_URL}/memory-blocks/archived/?${params.toString()}`, {
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

  // Keywords
  getKeywords: async () => {
    const response = await fetch(`${API_BASE_URL}/keywords`, {
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

  createKeyword: async (data) => {
    const response = await fetch(`${API_BASE_URL}/keywords`, {
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

  updateKeyword: async (id, data) => {
    const response = await fetch(`${API_BASE_URL}/keywords/${id}`, {
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

  deleteKeyword: async (id) => {
    const response = await fetch(`${API_BASE_URL}/keywords/${id}`, {
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
    return response.json();
  },

  // Memory Block Keywords Association
  addKeywordToMemoryBlock: async (memoryBlockId, keywordId) => {
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${memoryBlockId}/keywords/${keywordId}`, {
      method: 'POST',
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

  removeKeywordFromMemoryBlock: async (memoryBlockId, keywordId) => {
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${memoryBlockId}/keywords/${keywordId}`, {
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
    return response.json();
  },

  // Consolidation Suggestions
  getConsolidationSuggestions: async (filters = {}, signal) => {
    const { skip, limit, status, group_id, start_date, end_date, sort_by, sort_order } = filters;
    const params = new URLSearchParams({
      skip: skip || 0,
      limit: limit || 50,
      ...(status && { status }),
      ...(group_id && { group_id }),
      ...(start_date && { start_date }),
      ...(end_date && { end_date }),
      ...(sort_by && { sort_by }),
      ...(sort_order && { sort_order })
    });
    const response = await fetch(`${API_BASE_URL}/consolidation-suggestions/?${params.toString()}`, { 
      signal,
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

  getConsolidationSuggestionById: async (id) => {
    const response = await fetch(`${API_BASE_URL}/consolidation-suggestions/${id}`, {
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

  validateConsolidationSuggestion: async (id) => {
    const response = await fetch(`${API_BASE_URL}/consolidation-suggestions/${id}/validate/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
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

  rejectConsolidationSuggestion: async (id) => {
    const response = await fetch(`${API_BASE_URL}/consolidation-suggestions/${id}/reject/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
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
  triggerConsolidation: async () => {
    const response = await fetch(`${API_BASE_URL}/consolidation/trigger/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
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

  deleteConsolidationSuggestion: async (id) => {
    const response = await fetch(`${API_BASE_URL}/consolidation-suggestions/${id}`, {
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

  // Build Info
  getBuildInfo: async () => {
    const response = await fetch(`${API_BASE_URL}/build-info`, {
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

export default memoryService;

export const {
  getMemoryBlocks,
  getMemoryBlockById,
  updateMemoryBlock,
  archiveMemoryBlock, // Export the new function
  deleteMemoryBlock,
  getArchivedMemoryBlocks, // Export the new function
  getKeywords,
  createKeyword,
  updateKeyword,
  deleteKeyword,
  addKeywordToMemoryBlock,
  removeKeywordFromMemoryBlock,
  getConsolidationSuggestions,
  getConsolidationSuggestionById,
  validateConsolidationSuggestion,
  rejectConsolidationSuggestion,
  triggerConsolidation,
  deleteConsolidationSuggestion, // Export the new function
  getBuildInfo
} = memoryService;
