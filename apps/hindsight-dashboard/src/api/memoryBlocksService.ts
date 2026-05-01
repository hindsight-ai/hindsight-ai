import { apiFetch, guardGuest, jsonOrThrow } from './http';

export interface MemoryBlock {
  id: string;
  agent_id: string;
  content: string;
  visibility_scope?: string;
  organization_id?: string | null;
}

export const getMemoryBlocks = async (filters: Record<string, any> = {}) => {
  const { per_page, include_archived = false, ...rest } = filters;
  const params = new URLSearchParams({ ...rest, include_archived: String(include_archived) });
  if (per_page != null) params.set('limit', String(per_page));
  const resp = await apiFetch('/memory-blocks/', { ensureTrailingSlash: true, searchParams: params });
  return jsonOrThrow(resp);
};

export const getMemoryBlockById = async (id: string): Promise<MemoryBlock> => {
  const resp = await apiFetch(`/memory-blocks/${id}`);
  return jsonOrThrow(resp);
};

export const createMemoryBlock = async (
  data: Record<string, any>,
  opts?: { scopeOverride?: { scope: 'personal' | 'organization' | 'public'; organizationId?: string | null } }
) => {
  guardGuest('Sign in to create memory blocks.');
  const resp = await apiFetch('/memory-blocks/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    ensureTrailingSlash: true,
    scopeOverride: opts?.scopeOverride,
  });
  return jsonOrThrow(resp);
};

export const updateMemoryBlock = async (id: string, data: Partial<MemoryBlock>) => {
  guardGuest('Sign in to edit memory blocks.');
  const resp = await apiFetch(`/memory-blocks/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return jsonOrThrow(resp);
};

export const archiveMemoryBlock = async (id: string) => {
  guardGuest('Sign in to archive memory blocks.');
  const resp = await apiFetch(`/memory-blocks/${id}/archive`, { method: 'POST' });
  return jsonOrThrow(resp);
};

export const deleteMemoryBlock = async (id: string) => {
  guardGuest('Sign in to delete memory blocks.');
  const resp = await apiFetch(`/memory-blocks/${id}/hard-delete`, { method: 'DELETE' });
  if (resp.status === 204) { return; }
  try { return await resp.json(); } catch { return; }
};

export const getArchivedMemoryBlocks = async (filters: Record<string, any> = {}) => {
  const { per_page, ...rest } = filters;
  const params = new URLSearchParams(rest);
  if (per_page != null) params.set('limit', String(per_page));
  const resp = await apiFetch('/memory-blocks/archived/', { ensureTrailingSlash: true, searchParams: params });
  return jsonOrThrow(resp);
};

const memoryBlocksService = {
  getMemoryBlocks,
  getMemoryBlockById,
  createMemoryBlock,
  updateMemoryBlock,
  archiveMemoryBlock,
  deleteMemoryBlock,
  getArchivedMemoryBlocks,
};

export default memoryBlocksService;
