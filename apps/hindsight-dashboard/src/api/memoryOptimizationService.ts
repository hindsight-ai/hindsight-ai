import { apiFetch, guardGuest, jsonOrThrow } from './http';
import { getScope } from './scopeProvider';

export const getMemoryOptimizationSuggestions = async (filters: Record<string, any> = {}) => {
  const params = new URLSearchParams();
  if (filters.agentId) params.append('agent_id', filters.agentId);
  if (filters.priority) params.append('priority', filters.priority);
  if (filters.dateRange) params.append('date_range', filters.dateRange);
  try {
    const { scope, orgId } = getScope();
    if (scope) params.set('scope', scope);
    if (scope === 'organization' && orgId) params.set('organization_id', orgId);
  } catch {}
  const resp = await apiFetch('/memory-optimization/suggestions', { searchParams: params });
  return jsonOrThrow(resp);
};

export const executeOptimizationSuggestion = async (suggestionId: string, signal?: AbortSignal) => {
  guardGuest('Sign in to execute optimization suggestions.');
  const resp = await apiFetch(`/memory-optimization/suggestions/${suggestionId}/execute`, {
    method: 'POST',
    signal,
  });
  return jsonOrThrow(resp);
};

export const getSuggestionDetails = async (suggestionId: string) => {
  const resp = await apiFetch(`/memory-optimization/suggestions/${suggestionId}`);
  return jsonOrThrow(resp);
};

const memoryOptimizationService = {
  getMemoryOptimizationSuggestions,
  executeOptimizationSuggestion,
  getSuggestionDetails,
};

export default memoryOptimizationService;
