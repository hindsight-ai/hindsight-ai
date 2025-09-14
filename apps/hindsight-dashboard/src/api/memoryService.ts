import notificationService from '../services/notificationService';
import { apiFetch } from './http';

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
    if (per_page != null) params.set('limit', String(per_page));
    const resp = await apiFetch('/memory-blocks/', { ensureTrailingSlash: true, searchParams: params });
    return jsonOrThrow(resp);
  },
  contactSupport: async (payload: Record<string, any>) => {
    guardGuest('Sign in to contact support.');
    const resp = await apiFetch('/support/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (resp.status === 429) {
      // Surface rate-limit message clearly
      try {
        const data = await resp.json();
        const msg = data?.detail || `Please wait before sending another support request.`;
        throw new Error(msg);
      } catch {
        throw new Error('Please wait before sending another support request.');
      }
    }
    return jsonOrThrow(resp);
  },
  getMemoryBlockById: async (id: string): Promise<MemoryBlock> => {
    const resp = await apiFetch(`/memory-blocks/${id}`);
    return jsonOrThrow(resp);
  },
  updateMemoryBlock: async (id: string, data: Partial<MemoryBlock>) => { guardGuest('Sign in to edit memory blocks.'); const resp = await apiFetch(`/memory-blocks/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return jsonOrThrow(resp); },
  archiveMemoryBlock: async (id: string) => { guardGuest('Sign in to archive memory blocks.'); const resp = await apiFetch(`/memory-blocks/${id}/archive`, { method: 'POST' }); return jsonOrThrow(resp); },
  deleteMemoryBlock: async (id: string) => { guardGuest('Sign in to delete memory blocks.'); const resp = await apiFetch(`/memory-blocks/${id}/hard-delete`, { method: 'DELETE' }); if (!resp.ok && resp.status !== 204) { authFail(resp.status); throw new Error(`HTTP error ${resp.status}`); } if (resp.status === 204) { return; } try { return await resp.json(); } catch { return; } },
  getArchivedMemoryBlocks: async (filters: Record<string, any> = {}) => {
    const { per_page, ...rest } = filters; const params = new URLSearchParams(rest);
    if (per_page != null) params.set('limit', String(per_page));
    const resp = await apiFetch('/memory-blocks/archived/', { ensureTrailingSlash: true, searchParams: params });
    return jsonOrThrow(resp);
  },
  getKeywords: async (filters: Record<string, any> = {}) => { const params = new URLSearchParams(filters); const resp = await apiFetch('/keywords/', { ensureTrailingSlash: true, searchParams: params }); return jsonOrThrow(resp); },
  createKeyword: async (data: Record<string, any>) => { guardGuest('Sign in to create keywords.'); const resp = await apiFetch('/keywords/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return jsonOrThrow(resp); },
  updateKeyword: async (id: string, data: Record<string, any>) => { guardGuest('Sign in to update keywords.'); const resp = await apiFetch(`/keywords/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return jsonOrThrow(resp); },
  deleteKeyword: async (id: string) => { guardGuest('Sign in to delete keywords.'); const resp = await apiFetch(`/keywords/${id}`, { method: 'DELETE' }); return jsonOrThrow(resp); },
  getKeywordMemoryBlocks: async (keywordId: string, skip = 0, limit = 50) => { const params = new URLSearchParams({ skip: String(skip), limit: String(limit) }); const resp = await apiFetch(`/keywords/${keywordId}/memory-blocks/`, { ensureTrailingSlash: true, searchParams: params }); return jsonOrThrow(resp); },
  getKeywordMemoryBlocksCount: async (keywordId: string) => { const resp = await apiFetch(`/keywords/${keywordId}/memory-blocks/count`); return jsonOrThrow(resp); },
  addKeywordToMemoryBlock: async (memoryBlockId: string, keywordId: string) => { guardGuest('Sign in to add keywords.'); const resp = await apiFetch(`/memory-blocks/${memoryBlockId}/keywords/${keywordId}`, { method: 'POST' }); return jsonOrThrow(resp); },
  removeKeywordFromMemoryBlock: async (memoryBlockId: string, keywordId: string) => { guardGuest('Sign in to remove keywords.'); const resp = await apiFetch(`/memory-blocks/${memoryBlockId}/keywords/${keywordId}`, { method: 'DELETE' }); return jsonOrThrow(resp); },
  getConsolidationSuggestions: async (filters: Record<string, any> = {}, signal?: AbortSignal) => {
    const { skip, limit, status, group_id, start_date, end_date, sort_by, sort_order } = filters;
    const params = new URLSearchParams({ skip: String(skip || 0), limit: String(limit || 50) });
    if (status) params.set('status', status);
    if (group_id) params.set('group_id', group_id);
    if (start_date) params.set('start_date', start_date);
    if (end_date) params.set('end_date', end_date);
    if (sort_by) params.set('sort_by', sort_by);
    if (sort_order) params.set('sort_order', sort_order);
    try { const scope = sessionStorage.getItem('ACTIVE_SCOPE'); const orgId = sessionStorage.getItem('ACTIVE_ORG_ID'); if (scope) params.set('scope', scope); if (scope === 'organization' && orgId) params.set('organization_id', orgId); } catch {}
    const resp = await apiFetch('/consolidation-suggestions/', { ensureTrailingSlash: true, searchParams: params, signal });
    return jsonOrThrow(resp);
  },
  getConsolidationSuggestionById: async (id: string) => { const resp = await apiFetch(`/consolidation-suggestions/${id}`); return jsonOrThrow(resp); },
  validateConsolidationSuggestion: async (id: string) => { guardGuest('Sign in to validate suggestions.'); const resp = await apiFetch(`/consolidation-suggestions/${id}/validate/`, { method: 'POST', headers: { 'Content-Type': 'application/json' } }); return jsonOrThrow(resp); },
  rejectConsolidationSuggestion: async (id: string) => { guardGuest('Sign in to reject suggestions.'); const resp = await apiFetch(`/consolidation-suggestions/${id}/reject/`, { method: 'POST', headers: { 'Content-Type': 'application/json' } }); return jsonOrThrow(resp); },
  triggerConsolidation: async () => { guardGuest('Sign in to trigger consolidation.'); const resp = await apiFetch('/consolidation/trigger/', { method: 'POST' }); return jsonOrThrow(resp); },
  deleteConsolidationSuggestion: async (id: string) => { guardGuest('Sign in to delete suggestions.'); const resp = await apiFetch(`/consolidation-suggestions/${id}`, { method: 'DELETE' }); if (!resp.ok && resp.status !== 204) { authFail(resp.status); throw new Error(`HTTP error ${resp.status}`); } if (resp.status === 204) { return; } try { return await resp.json(); } catch { return; } },
  generatePruningSuggestions: async (params: Record<string, any> = {}) => { const resp = await apiFetch('/memory/prune/suggest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(params) }); return jsonOrThrow(resp); },
  confirmPruning: async (memoryBlockIds: string[]) => { const resp = await apiFetch('/memory/prune/confirm', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ memory_block_ids: memoryBlockIds }) }); return jsonOrThrow(resp); },
  getBuildInfo: async () => { const resp = await apiFetch('/build-info'); return jsonOrThrow(resp); },
  getConversationsCount: async () => {
    const params = new URLSearchParams();
    const resp = await apiFetch('/conversations/count', { searchParams: params });
    return jsonOrThrow(resp);
  },
  suggestKeywords: async (memoryBlockId: string) => { guardGuest('Sign in to generate keyword suggestions.'); const resp = await apiFetch(`/memory-blocks/${memoryBlockId}/suggest-keywords`, { method: 'POST', headers: { 'Content-Type': 'application/json' } }); return jsonOrThrow(resp); },
  compressMemoryBlock: async (memoryBlockId: string, userInstructions: Record<string, any> = {}) => { guardGuest('Sign in to compress memory blocks.'); const resp = await apiFetch(`/memory-blocks/${memoryBlockId}/compress`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(userInstructions) }); return jsonOrThrow(resp); },
  applyMemoryCompression: async (memoryBlockId: string, compressionData: Record<string, any>) => { guardGuest('Sign in to apply compression.'); const resp = await apiFetch(`/memory-blocks/${memoryBlockId}/compress/apply`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(compressionData) }); return jsonOrThrow(resp); },
  getMemoryOptimizationSuggestions: async (filters: Record<string, any> = {}) => {
    const params = new URLSearchParams();
    if (filters.agentId) params.append('agent_id', filters.agentId);
    if (filters.priority) params.append('priority', filters.priority);
    if (filters.dateRange) params.append('date_range', filters.dateRange);
    try { const scope = sessionStorage.getItem('ACTIVE_SCOPE'); const orgId = sessionStorage.getItem('ACTIVE_ORG_ID'); if (scope) params.set('scope', scope); if (scope === 'organization' && orgId) params.set('organization_id', orgId); } catch {}
    const resp = await apiFetch('/memory-optimization/suggestions', { searchParams: params });
    return jsonOrThrow(resp);
  },
  executeOptimizationSuggestion: async (suggestionId: string, signal?: AbortSignal) => { guardGuest('Sign in to execute optimization suggestions.'); const resp = await apiFetch(`/memory-optimization/suggestions/${suggestionId}/execute`, { method: 'POST', signal }); return jsonOrThrow(resp); },
  getSuggestionDetails: async (suggestionId: string) => { const resp = await apiFetch(`/memory-optimization/suggestions/${suggestionId}`); return jsonOrThrow(resp); },
  bulkCompactMemoryBlocks: async (memoryBlockIds: string[], userInstructions = '', maxConcurrent = 4, signal?: AbortSignal) => { guardGuest('Sign in to bulk compact.'); const resp = await apiFetch('/memory-blocks/bulk-compact', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ memory_block_ids: memoryBlockIds, user_instructions: userInstructions, max_concurrent: maxConcurrent }), signal }); return jsonOrThrow(resp); },
  bulkGenerateKeywords: async (memoryBlockIds: string[], signal?: AbortSignal) => { guardGuest('Sign in to bulk generate keywords.'); const resp = await apiFetch('/memory-blocks/bulk-generate-keywords', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ memory_block_ids: memoryBlockIds }), signal }); return jsonOrThrow(resp); },
  bulkApplyKeywords: async (applications: any[], signal?: AbortSignal) => { guardGuest('Sign in to bulk apply keywords.'); const resp = await apiFetch('/memory-blocks/bulk-apply-keywords', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ applications }), signal }); return jsonOrThrow(resp); },
  mergeMemoryBlocks: async (memoryBlockIds: string[], mergedContent: string) => { guardGuest('Sign in to merge memory blocks.'); const resp = await apiFetch('/memory-blocks/merge', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ memory_block_ids: memoryBlockIds, merged_content: mergedContent }) }); return jsonOrThrow(resp); },
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
export const { getMemoryBlocks, getMemoryBlockById, updateMemoryBlock, archiveMemoryBlock, deleteMemoryBlock, getArchivedMemoryBlocks, getKeywords, createKeyword, updateKeyword, deleteKeyword, addKeywordToMemoryBlock, removeKeywordFromMemoryBlock, getConsolidationSuggestions, getConsolidationSuggestionById, validateConsolidationSuggestion, rejectConsolidationSuggestion, triggerConsolidation, deleteConsolidationSuggestion, generatePruningSuggestions, confirmPruning, getBuildInfo, getConversationsCount, suggestKeywords, compressMemoryBlock, applyMemoryCompression, getMemoryOptimizationSuggestions, executeOptimizationSuggestion, getSuggestionDetails, bulkCompactMemoryBlocks, bulkGenerateKeywords, bulkApplyKeywords, mergeMemoryBlocks, contactSupport } = memoryService;
