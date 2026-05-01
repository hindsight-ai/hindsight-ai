import { apiFetch, guardGuest, jsonOrThrow } from './http';

export interface Keyword {
  keyword_id: string;
  keyword_text: string;
}

export const getKeywords = async (filters: Record<string, any> = {}) => {
  const params = new URLSearchParams(filters);
  const resp = await apiFetch('/keywords/', { ensureTrailingSlash: true, searchParams: params });
  return jsonOrThrow(resp);
};

export const createKeyword = async (
  data: Record<string, any>,
  opts?: { scopeOverride?: { scope: 'personal' | 'organization' | 'public'; organizationId?: string | null } }
) => {
  guardGuest('Sign in to create keywords.');
  const resp = await apiFetch('/keywords/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    scopeOverride: opts?.scopeOverride,
  });
  return jsonOrThrow(resp);
};

export const updateKeyword = async (id: string, data: Record<string, any>) => {
  guardGuest('Sign in to update keywords.');
  const resp = await apiFetch(`/keywords/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return jsonOrThrow(resp);
};

export const deleteKeyword = async (id: string) => {
  guardGuest('Sign in to delete keywords.');
  const resp = await apiFetch(`/keywords/${id}`, { method: 'DELETE' });
  return jsonOrThrow(resp);
};

export const getKeywordMemoryBlocks = async (keywordId: string, skip = 0, limit = 50) => {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  const resp = await apiFetch(`/keywords/${keywordId}/memory-blocks/`, { ensureTrailingSlash: true, searchParams: params });
  return jsonOrThrow(resp);
};

export const getKeywordMemoryBlocksCount = async (keywordId: string) => {
  const resp = await apiFetch(`/keywords/${keywordId}/memory-blocks/count`);
  return jsonOrThrow(resp);
};

export const addKeywordToMemoryBlock = async (memoryBlockId: string, keywordId: string) => {
  guardGuest('Sign in to add keywords.');
  const resp = await apiFetch(`/memory-blocks/${memoryBlockId}/keywords/${keywordId}`, { method: 'POST' });
  return jsonOrThrow(resp);
};

export const removeKeywordFromMemoryBlock = async (memoryBlockId: string, keywordId: string) => {
  guardGuest('Sign in to remove keywords.');
  const resp = await apiFetch(`/memory-blocks/${memoryBlockId}/keywords/${keywordId}`, { method: 'DELETE' });
  return jsonOrThrow(resp);
};

export const suggestKeywords = async (memoryBlockId: string) => {
  guardGuest('Sign in to generate keyword suggestions.');
  const resp = await apiFetch(`/memory-blocks/${memoryBlockId}/suggest-keywords`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return jsonOrThrow(resp);
};

const keywordsService = {
  getKeywords,
  createKeyword,
  updateKeyword,
  deleteKeyword,
  getKeywordMemoryBlocks,
  getKeywordMemoryBlocksCount,
  addKeywordToMemoryBlock,
  removeKeywordFromMemoryBlock,
  suggestKeywords,
};

export default keywordsService;
