import notificationService from '../services/notificationService';

const isGuest = (): boolean => { try { return sessionStorage.getItem('GUEST_MODE') === 'true'; } catch { return false; } };

let API_BASE_URL: string = '/api';
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
    const url = new URL(API_BASE_URL);
    if (isHttps && url.protocol === 'http:') {
      url.protocol = 'https:';
      API_BASE_URL = url.toString().replace(/\/$/, '');
    }
  }
} catch {}

const base = () => {
  const relativeUrl = isGuest() ? '/guest-api' : API_BASE_URL;
  
  // Convert to absolute URL to avoid browser base URL resolution issues
  let absoluteUrl;
  if (typeof window !== 'undefined') {
    // In development, ensure we use the correct port
    const currentOrigin = window.location.origin;
    const isDev = currentOrigin.includes(':3000');
    
    if (isDev) {
      absoluteUrl = `http://localhost:3000${relativeUrl}`;
    } else {
      // In production, use current origin
      absoluteUrl = `${currentOrigin}${relativeUrl}`;
    }
  } else {
    absoluteUrl = relativeUrl; // Fallback for server-side rendering
  }
  
  console.log('[DEBUG] memoryService base URL:', absoluteUrl, 'original:', relativeUrl, 'origin:', typeof window !== 'undefined' ? window.location.origin : 'N/A');
  return absoluteUrl;
};

export interface MemoryBlock { id: string; agent_id: string; content: string; visibility_scope?: string; organization_id?: string | null; }
export interface Keyword { keyword_id: string; keyword_text: string; }
export interface ConsolidationSuggestion {
  suggestion_id: string;
  status: string;
  group_id?: string;
  suggested_content?: string;
  original_memory_ids?: string[];
}

type AbortOpt = { signal?: AbortSignal };

const authFail = (status: number) => {
  if (status === 401) { notificationService.show401Error(); throw new Error('Authentication required'); }
};

const jsonOrThrow = async (resp: Response) => {
  if (!resp.ok) { authFail(resp.status); throw new Error(`HTTP error ${resp.status}`); }
  return resp.json();
};

const guardGuest = (action: string) => { if (isGuest()) { notificationService.showWarning(`Guest mode is read-only. ${action}`); throw new Error('Guest mode read-only'); } };

const memoryService = {
  getMemoryBlocks: async (filters: Record<string, any> = {}) => {
    const { per_page, include_archived = false, ...rest } = filters;
    const params = new URLSearchParams({ ...rest, include_archived: String(include_archived) });
    try { const scope = sessionStorage.getItem('ACTIVE_SCOPE'); const orgId = sessionStorage.getItem('ACTIVE_ORG_ID'); if (scope) params.set('scope', scope); if (scope === 'organization' && orgId) params.set('organization_id', orgId); } catch {}
    if (per_page != null) params.append('limit', String(per_page));
    const resp = await fetch(`${base()}/memory-blocks/?${params.toString()}`, { credentials: 'include' });
    return jsonOrThrow(resp);
  },
  getMemoryBlockById: async (id: string): Promise<MemoryBlock> => jsonOrThrow(await fetch(`${base()}/memory-blocks/${id}`, { credentials: 'include' })),
  updateMemoryBlock: async (id: string, data: Partial<MemoryBlock>) => { guardGuest('Sign in to edit memory blocks.'); const resp = await fetch(`${API_BASE_URL}/memory-blocks/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data), credentials: 'include' }); return jsonOrThrow(resp); },
  archiveMemoryBlock: async (id: string) => { guardGuest('Sign in to archive memory blocks.'); const resp = await fetch(`${API_BASE_URL}/memory-blocks/${id}/archive`, { method: 'POST', credentials: 'include' }); return jsonOrThrow(resp); },
  deleteMemoryBlock: async (id: string) => { guardGuest('Sign in to delete memory blocks.'); const resp = await fetch(`${API_BASE_URL}/memory-blocks/${id}/hard-delete`, { method: 'DELETE', credentials: 'include' }); if (!resp.ok && resp.status !== 204) { authFail(resp.status); throw new Error(`HTTP error ${resp.status}`); } if (resp.status === 204) { return; } try { return await resp.json(); } catch { return; } },
  getArchivedMemoryBlocks: async (filters: Record<string, any> = {}) => {
    const { per_page, ...rest } = filters; const params = new URLSearchParams(rest);
    try { const scope = sessionStorage.getItem('ACTIVE_SCOPE'); const orgId = sessionStorage.getItem('ACTIVE_ORG_ID'); if (scope) params.set('scope', scope); if (scope === 'organization' && orgId) params.set('organization_id', orgId); } catch {}
    if (per_page != null) params.append('limit', String(per_page));
    const url = `${base()}/memory-blocks/archived/?${params.toString()}`;
    console.log('[DEBUG] getArchivedMemoryBlocks URL:', url);
    return jsonOrThrow(await fetch(url, { credentials: 'include' }));
  },
  getKeywords: async (filters: Record<string, any> = {}) => { const params = new URLSearchParams(filters); try { const scope = sessionStorage.getItem('ACTIVE_SCOPE'); const orgId = sessionStorage.getItem('ACTIVE_ORG_ID'); if (scope) params.set('scope', scope); if (scope === 'organization' && orgId) params.set('organization_id', orgId); } catch {}; const url = `${base()}/keywords/${params.toString() ? `?${params.toString()}` : ''}`; return jsonOrThrow(await fetch(url, { credentials: 'include' })); },
  createKeyword: async (data: Record<string, any>) => { guardGuest('Sign in to create keywords.'); const resp = await fetch(`${API_BASE_URL}/keywords/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data), credentials: 'include' }); return jsonOrThrow(resp); },
  updateKeyword: async (id: string, data: Record<string, any>) => { guardGuest('Sign in to update keywords.'); const resp = await fetch(`${API_BASE_URL}/keywords/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data), credentials: 'include' }); return jsonOrThrow(resp); },
  deleteKeyword: async (id: string) => { guardGuest('Sign in to delete keywords.'); const resp = await fetch(`${API_BASE_URL}/keywords/${id}`, { method: 'DELETE', credentials: 'include' }); return jsonOrThrow(resp); },
  getKeywordMemoryBlocks: async (keywordId: string, skip = 0, limit = 50) => jsonOrThrow(await fetch(`${base()}/keywords/${keywordId}/memory-blocks/?${new URLSearchParams({ skip: String(skip), limit: String(limit) }).toString()}`, { credentials: 'include' })),
  getKeywordMemoryBlocksCount: async (keywordId: string) => jsonOrThrow(await fetch(`${base()}/keywords/${keywordId}/memory-blocks/count`, { credentials: 'include' })),
  addKeywordToMemoryBlock: async (memoryBlockId: string, keywordId: string) => { guardGuest('Sign in to add keywords.'); return jsonOrThrow(await fetch(`${API_BASE_URL}/memory-blocks/${memoryBlockId}/keywords/${keywordId}`, { method: 'POST', credentials: 'include' })); },
  removeKeywordFromMemoryBlock: async (memoryBlockId: string, keywordId: string) => { guardGuest('Sign in to remove keywords.'); return jsonOrThrow(await fetch(`${API_BASE_URL}/memory-blocks/${memoryBlockId}/keywords/${keywordId}`, { method: 'DELETE', credentials: 'include' })); },
  getConsolidationSuggestions: async (filters: Record<string, any> = {}, signal?: AbortSignal) => { const { skip, limit, status, group_id, start_date, end_date, sort_by, sort_order } = filters; const params = new URLSearchParams({ skip: String(skip || 0), limit: String(limit || 50) }); if (status) params.set('status', status); if (group_id) params.set('group_id', group_id); if (start_date) params.set('start_date', start_date); if (end_date) params.set('end_date', end_date); if (sort_by) params.set('sort_by', sort_by); if (sort_order) params.set('sort_order', sort_order); return jsonOrThrow(await fetch(`${base()}/consolidation-suggestions/?${params.toString()}`, { credentials: 'include', signal })); },
  getConsolidationSuggestionById: async (id: string) => jsonOrThrow(await fetch(`${base()}/consolidation-suggestions/${id}`, { credentials: 'include' })),
  validateConsolidationSuggestion: async (id: string) => { guardGuest('Sign in to validate suggestions.'); return jsonOrThrow(await fetch(`${API_BASE_URL}/consolidation-suggestions/${id}/validate/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include' })); },
  rejectConsolidationSuggestion: async (id: string) => { guardGuest('Sign in to reject suggestions.'); return jsonOrThrow(await fetch(`${API_BASE_URL}/consolidation-suggestions/${id}/reject/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include' })); },
  triggerConsolidation: async () => { guardGuest('Sign in to trigger consolidation.'); return jsonOrThrow(await fetch(`${API_BASE_URL}/consolidation/trigger/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include' })); },
  deleteConsolidationSuggestion: async (id: string) => { guardGuest('Sign in to delete suggestions.'); const resp = await fetch(`${API_BASE_URL}/consolidation-suggestions/${id}`, { method: 'DELETE', credentials: 'include' }); if (!resp.ok && resp.status !== 204) { authFail(resp.status); throw new Error(`HTTP error ${resp.status}`); } if (resp.status === 204) { return; } try { return await resp.json(); } catch { return; } },
  generatePruningSuggestions: async (params: Record<string, any> = {}) => jsonOrThrow(await fetch(`${API_BASE_URL}/memory/prune/suggest`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(params), credentials: 'include' })),
  confirmPruning: async (memoryBlockIds: string[]) => jsonOrThrow(await fetch(`${API_BASE_URL}/memory/prune/confirm`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ memory_block_ids: memoryBlockIds }), credentials: 'include' })),
  getBuildInfo: async () => jsonOrThrow(await fetch(`${base()}/build-info`, { credentials: 'include' })),
  getConversationsCount: async () => jsonOrThrow(await fetch(`${base()}/conversations/count`, { credentials: 'include' })),
  suggestKeywords: async (memoryBlockId: string) => { guardGuest('Sign in to generate keyword suggestions.'); return jsonOrThrow(await fetch(`${API_BASE_URL}/memory-blocks/${memoryBlockId}/suggest-keywords`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include' })); },
  compressMemoryBlock: async (memoryBlockId: string, userInstructions: Record<string, any> = {}) => { guardGuest('Sign in to compress memory blocks.'); return jsonOrThrow(await fetch(`${API_BASE_URL}/memory-blocks/${memoryBlockId}/compress`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(userInstructions), credentials: 'include' })); },
  applyMemoryCompression: async (memoryBlockId: string, compressionData: Record<string, any>) => { guardGuest('Sign in to apply compression.'); return jsonOrThrow(await fetch(`${API_BASE_URL}/memory-blocks/${memoryBlockId}/compress/apply`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(compressionData), credentials: 'include' })); },
  getMemoryOptimizationSuggestions: async (filters: Record<string, any> = {}) => { const params = new URLSearchParams(); if (filters.agentId) params.append('agent_id', filters.agentId); if (filters.priority) params.append('priority', filters.priority); if (filters.dateRange) params.append('date_range', filters.dateRange); const url = `${base()}/memory-optimization/suggestions${params.toString() ? `?${params.toString()}` : ''}`; return jsonOrThrow(await fetch(url, { credentials: 'include' })); },
  executeOptimizationSuggestion: async (suggestionId: string, signal?: AbortSignal) => { guardGuest('Sign in to execute optimization suggestions.'); return jsonOrThrow(await fetch(`${API_BASE_URL}/memory-optimization/suggestions/${suggestionId}/execute`, { method: 'POST', credentials: 'include', signal })); },
  getSuggestionDetails: async (suggestionId: string) => jsonOrThrow(await fetch(`${base()}/memory-optimization/suggestions/${suggestionId}`, { credentials: 'include' })),
  bulkCompactMemoryBlocks: async (memoryBlockIds: string[], userInstructions = '', maxConcurrent = 4, signal?: AbortSignal) => { guardGuest('Sign in to bulk compact.'); return jsonOrThrow(await fetch(`${API_BASE_URL}/memory-blocks/bulk-compact`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ memory_block_ids: memoryBlockIds, user_instructions: userInstructions, max_concurrent: maxConcurrent }), credentials: 'include', signal })); },
  bulkGenerateKeywords: async (memoryBlockIds: string[], signal?: AbortSignal) => { guardGuest('Sign in to bulk generate keywords.'); return jsonOrThrow(await fetch(`${API_BASE_URL}/memory-blocks/bulk-generate-keywords`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ memory_block_ids: memoryBlockIds }), credentials: 'include', signal })); },
  bulkApplyKeywords: async (applications: any[], signal?: AbortSignal) => { guardGuest('Sign in to bulk apply keywords.'); return jsonOrThrow(await fetch(`${API_BASE_URL}/memory-blocks/bulk-apply-keywords`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ applications }), credentials: 'include', signal })); },
  mergeMemoryBlocks: async (memoryBlockIds: string[], mergedContent: string) => { guardGuest('Sign in to merge memory blocks.'); return jsonOrThrow(await fetch(`${API_BASE_URL}/memory-blocks/merge`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ memory_block_ids: memoryBlockIds, merged_content: mergedContent }), credentials: 'include' })); },
  bulkGenerateKeywordsBatched: async (memoryBlockIds: string[], { batchSize = 200, signal, onProgress }: { batchSize?: number; signal?: AbortSignal; onProgress?: (p: { processed: number; total: number }) => void } = {}) => {
    const total = memoryBlockIds.length; let processed = 0; const aggregate: any = { suggestions: [], successful_count: 0, failed_count: 0, total_processed: 0, message: '' };
    for (let i = 0; i < memoryBlockIds.length; i += batchSize) { if (signal?.aborted) throw new DOMException('Aborted', 'AbortError'); const batch = memoryBlockIds.slice(i, i + batchSize); const resp: any = await memoryService.bulkGenerateKeywords(batch, signal); aggregate.suggestions.push(...(resp.suggestions || [])); aggregate.successful_count += resp.successful_count || 0; aggregate.failed_count += resp.failed_count || 0; aggregate.total_processed += resp.total_processed || batch.length; processed += batch.length; onProgress && onProgress({ processed: Math.min(processed, total), total }); }
    aggregate.message = `Generated keyword suggestions for ${aggregate.successful_count} memory blocks`; return aggregate; },
  bulkApplyKeywordsBatched: async (applications: any[], { batchSize = 200, signal, onProgress }: { batchSize?: number; signal?: AbortSignal; onProgress?: (p: { processed: number; total: number }) => void } = {}) => {
    const total = applications.length; let processed = 0; const aggregate: any = { results: [], successful_count: 0, failed_count: 0, message: '' };
    for (let i = 0; i < applications.length; i += batchSize) { if (signal?.aborted) throw new DOMException('Aborted', 'AbortError'); const batch = applications.slice(i, i + batchSize); const resp: any = await memoryService.bulkApplyKeywords(batch, signal); aggregate.results.push(...(resp.results || [])); aggregate.successful_count += resp.successful_count || 0; aggregate.failed_count += resp.failed_count || 0; processed += batch.length; onProgress && onProgress({ processed: Math.min(processed, total), total }); }
    aggregate.message = `Applied keywords to ${aggregate.successful_count} memory blocks`; return aggregate; },
};

export default memoryService;
export const { getMemoryBlocks, getMemoryBlockById, updateMemoryBlock, archiveMemoryBlock, deleteMemoryBlock, getArchivedMemoryBlocks, getKeywords, createKeyword, updateKeyword, deleteKeyword, addKeywordToMemoryBlock, removeKeywordFromMemoryBlock, getConsolidationSuggestions, getConsolidationSuggestionById, validateConsolidationSuggestion, rejectConsolidationSuggestion, triggerConsolidation, deleteConsolidationSuggestion, generatePruningSuggestions, confirmPruning, getBuildInfo, getConversationsCount, suggestKeywords, compressMemoryBlock, applyMemoryCompression, getMemoryOptimizationSuggestions, executeOptimizationSuggestion, getSuggestionDetails, bulkCompactMemoryBlocks, bulkGenerateKeywords, bulkApplyKeywords, mergeMemoryBlocks } = memoryService;
