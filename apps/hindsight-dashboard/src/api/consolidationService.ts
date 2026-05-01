import { apiFetch, isGuest } from './http';
import { getScope } from './scopeProvider';

const guardGuest = (action: string) => { if (isGuest()) throw new Error(action); };

export interface ConsolidationSuggestion {
  suggestion_id: string;
  status: string;
  group_id?: string;
  suggested_content?: string;
  original_memory_ids?: string[];
}

type AbortOpt = { signal?: AbortSignal };

const jsonOrThrow = async (resp: Response) => resp.json();

export const getConsolidationSuggestions = async (filters: Record<string, any> = {}, signal?: AbortSignal) => {
  const { skip, limit, status, group_id, start_date, end_date, sort_by, sort_order } = filters;
  const params = new URLSearchParams({ skip: String(skip || 0), limit: String(limit || 50) });
  if (status) params.set('status', status);
  if (group_id) params.set('group_id', group_id);
  if (start_date) params.set('start_date', start_date);
  if (end_date) params.set('end_date', end_date);
  if (sort_by) params.set('sort_by', sort_by);
  if (sort_order) params.set('sort_order', sort_order);
  try {
    const { scope, orgId } = getScope();
    if (scope) params.set('scope', scope);
    if (scope === 'organization' && orgId) params.set('organization_id', orgId);
  } catch {}
  const resp = await apiFetch('/consolidation-suggestions/', { ensureTrailingSlash: true, searchParams: params, signal });
  return jsonOrThrow(resp);
};

export const getConsolidationSuggestionById = async (id: string) => {
  const resp = await apiFetch(`/consolidation-suggestions/${id}`);
  return jsonOrThrow(resp);
};

export const validateConsolidationSuggestion = async (id: string) => {
  guardGuest('Sign in to validate suggestions.');
  const resp = await apiFetch(`/consolidation-suggestions/${id}/validate/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return jsonOrThrow(resp);
};

export const rejectConsolidationSuggestion = async (id: string) => {
  guardGuest('Sign in to reject suggestions.');
  const resp = await apiFetch(`/consolidation-suggestions/${id}/reject/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return jsonOrThrow(resp);
};

export const triggerConsolidation = async () => {
  guardGuest('Sign in to trigger consolidation.');
  const resp = await apiFetch('/consolidation/trigger/', { method: 'POST' });
  return jsonOrThrow(resp);
};

export const deleteConsolidationSuggestion = async (id: string) => {
  guardGuest('Sign in to delete suggestions.');
  const resp = await apiFetch(`/consolidation-suggestions/${id}`, { method: 'DELETE' });
  if (resp.status === 204) { return; }
  try { return await resp.json(); } catch { return; }
};

const consolidationService = {
  getConsolidationSuggestions,
  getConsolidationSuggestionById,
  validateConsolidationSuggestion,
  rejectConsolidationSuggestion,
  triggerConsolidation,
  deleteConsolidationSuggestion,
};

export default consolidationService;
