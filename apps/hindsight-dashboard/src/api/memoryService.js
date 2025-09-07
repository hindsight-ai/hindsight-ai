import notificationService from '../services/notificationService';

const isGuest = () => {
  try { return sessionStorage.getItem('GUEST_MODE') === 'true'; } catch { return false; }
};
const base = () => (isGuest() ? '/guest-api' : API_BASE_URL);

// Prefer runtime env first; fall back to process env or relative '/api'
let API_BASE_URL = '/api';
try {
  if (typeof window !== 'undefined' && window.__ENV__ && window.__ENV__.HINDSIGHT_SERVICE_API_URL) {
    API_BASE_URL = window.__ENV__.HINDSIGHT_SERVICE_API_URL;
  } else if (typeof process !== 'undefined' && process.env && process.env.VITE_HINDSIGHT_SERVICE_API_URL) {
    API_BASE_URL = process.env.VITE_HINDSIGHT_SERVICE_API_URL;
  }
} catch {}

// Upgrade API scheme at runtime to avoid mixed content when app is served over HTTPS
try {
  if (typeof window !== 'undefined' && API_BASE_URL) {
    const isHttps = window.location.protocol === 'https:';
    const url = new URL(API_BASE_URL);
    if (isHttps && url.protocol === 'http:') {
      url.protocol = 'https:';
      API_BASE_URL = url.toString().replace(/\/$/, '');
    }
  }
} catch (_) {
  // Ignore URL parsing errors and use the env value as-is
}

// When using relative '/api', this remains same-origin via Nginx proxy

const memoryService = {
  // Memory Blocks
  getMemoryBlocks: async (filters = {}) => {
    const { per_page, include_archived = false, ...rest } = filters; // Destructure include_archived with default false
    const params = new URLSearchParams({ ...rest, include_archived }); // Start with rest and include_archived

    // Attach active scope selection
    try {
      const scope = sessionStorage.getItem('ACTIVE_SCOPE');
      const orgId = sessionStorage.getItem('ACTIVE_ORG_ID');
      if (scope) params.set('scope', scope);
      if (scope === 'organization' && orgId) params.set('organization_id', orgId);
    } catch {}

    // Only add limit if per_page is defined and not null/undefined
    if (per_page !== undefined && per_page !== null) {
      params.append('limit', per_page.toString());
    }

    const response = await fetch(`${base()}/memory-blocks/?${params.toString()}`, {
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
    const response = await fetch(`${base()}/memory-blocks/${id}`, {
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
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to edit memory blocks.'); throw new Error('Guest mode read-only'); }
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
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to archive memory blocks.'); throw new Error('Guest mode read-only'); }
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
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to delete memory blocks.'); throw new Error('Guest mode read-only'); }
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
    const params = new URLSearchParams(rest); // Start with rest parameters

    // Attach active scope selection
    try {
      const scope = sessionStorage.getItem('ACTIVE_SCOPE');
      const orgId = sessionStorage.getItem('ACTIVE_ORG_ID');
      if (scope) params.set('scope', scope);
      if (scope === 'organization' && orgId) params.set('organization_id', orgId);
    } catch {}

    // Only add limit if per_page is defined and not null/undefined
    if (per_page !== undefined && per_page !== null) {
      params.append('limit', per_page.toString());
    }

    const response = await fetch(`${base()}/memory-blocks/archived/?${params.toString()}`, {
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
  getKeywords: async (filters = {}) => {
    const params = new URLSearchParams(filters || {});
    try {
      const scope = sessionStorage.getItem('ACTIVE_SCOPE');
      const orgId = sessionStorage.getItem('ACTIVE_ORG_ID');
      if (scope) params.set('scope', scope);
      if (scope === 'organization' && orgId) params.set('organization_id', orgId);
    } catch {}
    const url = `${base()}/keywords/${params.toString() ? `?${params.toString()}` : ''}`;
    const response = await fetch(url, {
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
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to create keywords.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/keywords/`, {
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
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to update keywords.'); throw new Error('Guest mode read-only'); }
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
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to delete keywords.'); throw new Error('Guest mode read-only'); }
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

  getKeywordMemoryBlocks: async (keywordId, skip = 0, limit = 50) => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString()
    });
    const response = await fetch(`${base()}/keywords/${keywordId}/memory-blocks/?${params.toString()}`, {
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

  getKeywordMemoryBlocksCount: async (keywordId) => {
    const response = await fetch(`${base()}/keywords/${keywordId}/memory-blocks/count`, {
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
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to add keywords.'); throw new Error('Guest mode read-only'); }
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
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to remove keywords.'); throw new Error('Guest mode read-only'); }
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
    const response = await fetch(`${base()}/consolidation-suggestions/?${params.toString()}`, { 
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
    const response = await fetch(`${base()}/consolidation-suggestions/${id}`, {
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
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to validate suggestions.'); throw new Error('Guest mode read-only'); }
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
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to reject suggestions.'); throw new Error('Guest mode read-only'); }
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
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to trigger consolidation.'); throw new Error('Guest mode read-only'); }
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
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to delete suggestions.'); throw new Error('Guest mode read-only'); }
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

  // Pruning Endpoints
  generatePruningSuggestions: async (params = {}) => {
    const response = await fetch(`${API_BASE_URL}/memory/prune/suggest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
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

  confirmPruning: async (memoryBlockIds) => {
    const response = await fetch(`${API_BASE_URL}/memory/prune/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ memory_block_ids: memoryBlockIds }),
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

  // Build Info
  getBuildInfo: async () => {
    const response = await fetch(`${base()}/build-info`, {
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

  // Conversations Count
  getConversationsCount: async () => {
    const response = await fetch(`${base()}/conversations/count`, {
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

  // Suggest Keywords for Memory Block
  suggestKeywords: async (memoryBlockId) => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to generate keyword suggestions.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${memoryBlockId}/suggest-keywords`, {
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

  // Compress Memory Block
  compressMemoryBlock: async (memoryBlockId, userInstructions = {}) => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to compress memory blocks.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${memoryBlockId}/compress`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userInstructions),
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

  // Apply Memory Compression
  applyMemoryCompression: async (memoryBlockId, compressionData) => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to apply compression.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/memory-blocks/${memoryBlockId}/compress/apply`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(compressionData),
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

  // Memory Optimization Center
  getMemoryOptimizationSuggestions: async (filters = {}) => {
    const params = new URLSearchParams();
    
    // Add filter parameters if they exist
    if (filters.agentId) params.append('agent_id', filters.agentId);
    if (filters.priority) params.append('priority', filters.priority);
    if (filters.dateRange) params.append('date_range', filters.dateRange);
    
    const url = `${base()}/memory-optimization/suggestions${params.toString() ? `?${params.toString()}` : ''}`;
    
    const response = await fetch(url, {
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

  executeOptimizationSuggestion: async (suggestionId, signal) => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to execute optimization suggestions.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/memory-optimization/suggestions/${suggestionId}/execute`, {
      method: 'POST',
      credentials: 'include',
      signal,
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

  getSuggestionDetails: async (suggestionId) => {
    const response = await fetch(`${base()}/memory-optimization/suggestions/${suggestionId}`, {
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

  bulkCompactMemoryBlocks: async (memoryBlockIds, userInstructions = '', maxConcurrent = 4, signal) => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to bulk compact.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/memory-blocks/bulk-compact`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        memory_block_ids: memoryBlockIds,
        user_instructions: userInstructions,
        max_concurrent: maxConcurrent
      }),
      credentials: 'include',
      signal,
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

  bulkGenerateKeywords: async (memoryBlockIds, signal) => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to bulk generate keywords.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/memory-blocks/bulk-generate-keywords`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ memory_block_ids: memoryBlockIds }),
      credentials: 'include',
      signal,
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

  bulkApplyKeywords: async (applications, signal) => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to bulk apply keywords.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/memory-blocks/bulk-apply-keywords`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ applications }),
      credentials: 'include',
      signal,
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

  mergeMemoryBlocks: async (memoryBlockIds, mergedContent) => {
    if (isGuest()) { notificationService.showWarning('Guest mode is read-only. Sign in to merge memory blocks.'); throw new Error('Guest mode read-only'); }
    const response = await fetch(`${API_BASE_URL}/memory-blocks/merge`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        memory_block_ids: memoryBlockIds,
        merged_content: mergedContent 
      }),
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

  // --- New batched helpers for large datasets ---
  bulkGenerateKeywordsBatched: async (memoryBlockIds, { batchSize = 200, signal, onProgress } = {}) => {
    // Process IDs in batches to avoid very large payloads/timeouts
    const total = memoryBlockIds.length;
    let processed = 0;
    let aggregate = {
      suggestions: [],
      successful_count: 0,
      failed_count: 0,
      total_processed: 0,
      message: ''
    };

    for (let i = 0; i < memoryBlockIds.length; i += batchSize) {
      if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
      const batch = memoryBlockIds.slice(i, i + batchSize);
      const resp = await memoryService.bulkGenerateKeywords(batch, signal);
      aggregate.suggestions.push(...(resp.suggestions || []));
      aggregate.successful_count += resp.successful_count || 0;
      aggregate.failed_count += resp.failed_count || 0;
      aggregate.total_processed += resp.total_processed || batch.length;
      processed += batch.length;
      onProgress && onProgress({ processed: Math.min(processed, total), total });
    }

    aggregate.message = `Generated keyword suggestions for ${aggregate.successful_count} memory blocks`;
    return aggregate;
  },

  bulkApplyKeywordsBatched: async (applications, { batchSize = 200, signal, onProgress } = {}) => {
    const total = applications.length;
    let processed = 0;
    let aggregate = {
      results: [],
      successful_count: 0,
      failed_count: 0,
      message: ''
    };

    for (let i = 0; i < applications.length; i += batchSize) {
      if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
      const batch = applications.slice(i, i + batchSize);
      const resp = await memoryService.bulkApplyKeywords(batch, signal);
      aggregate.results.push(...(resp.results || []));
      aggregate.successful_count += resp.successful_count || 0;
      aggregate.failed_count += resp.failed_count || 0;
      processed += batch.length;
      onProgress && onProgress({ processed: Math.min(processed, total), total });
    }

    aggregate.message = `Applied keywords to ${aggregate.successful_count} memory blocks`;
    return aggregate;
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
  generatePruningSuggestions,
  confirmPruning,
  getBuildInfo,
  getMemoryOptimizationSuggestions,
  executeOptimizationSuggestion,
  getSuggestionDetails,
  bulkCompactMemoryBlocks,
  bulkGenerateKeywords,
  bulkApplyKeywords,
  mergeMemoryBlocks
} = memoryService;
