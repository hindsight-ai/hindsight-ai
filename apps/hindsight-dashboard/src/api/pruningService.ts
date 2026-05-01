import { apiFetch } from './http';

const jsonOrThrow = async (resp: Response) => resp.json();

export const generatePruningSuggestions = async (params: Record<string, any> = {}) => {
  const resp = await apiFetch('/memory/prune/suggest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return jsonOrThrow(resp);
};

export const confirmPruning = async (memoryBlockIds: string[]) => {
  const resp = await apiFetch('/memory/prune/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ memory_block_ids: memoryBlockIds }),
  });
  return jsonOrThrow(resp);
};

const pruningService = {
  generatePruningSuggestions,
  confirmPruning,
};

export default pruningService;
