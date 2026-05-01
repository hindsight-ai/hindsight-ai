import { apiFetch, guardGuest, jsonOrThrow } from './http';

export const compressMemoryBlock = async (memoryBlockId: string, userInstructions: Record<string, any> = {}) => {
  guardGuest('Sign in to compress memory blocks.');
  const resp = await apiFetch(`/memory-blocks/${memoryBlockId}/compress`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userInstructions),
  });
  return jsonOrThrow(resp);
};

export const applyMemoryCompression = async (memoryBlockId: string, compressionData: Record<string, any>) => {
  guardGuest('Sign in to apply compression.');
  const resp = await apiFetch(`/memory-blocks/${memoryBlockId}/compress/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(compressionData),
  });
  return jsonOrThrow(resp);
};

const compressionService = {
  compressMemoryBlock,
  applyMemoryCompression,
};

export default compressionService;
