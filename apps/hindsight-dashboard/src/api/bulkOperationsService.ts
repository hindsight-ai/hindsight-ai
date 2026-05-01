import { apiFetch, isGuest } from './http';

const guardGuest = (action: string) => { if (isGuest()) throw new Error(action); };

const jsonOrThrow = async (resp: Response) => resp.json();

export const bulkCompactMemoryBlocks = async (
  memoryBlockIds: string[],
  userInstructions = '',
  maxConcurrent = 4,
  signal?: AbortSignal
) => {
  guardGuest('Sign in to bulk compact.');
  const resp = await apiFetch('/memory-blocks/bulk-compact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      memory_block_ids: memoryBlockIds,
      user_instructions: userInstructions,
      max_concurrent: maxConcurrent,
    }),
    signal,
  });
  return jsonOrThrow(resp);
};

export const bulkGenerateKeywords = async (memoryBlockIds: string[], signal?: AbortSignal) => {
  guardGuest('Sign in to bulk generate keywords.');
  const resp = await apiFetch('/memory-blocks/bulk-generate-keywords', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ memory_block_ids: memoryBlockIds }),
    signal,
  });
  return jsonOrThrow(resp);
};

export const bulkApplyKeywords = async (applications: any[], signal?: AbortSignal) => {
  guardGuest('Sign in to bulk apply keywords.');
  const resp = await apiFetch('/memory-blocks/bulk-apply-keywords', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ applications }),
    signal,
  });
  return jsonOrThrow(resp);
};

// Batched variants call through the service object so callers can spy on
// bulkGenerateKeywords / bulkApplyKeywords at the service boundary.
export const bulkGenerateKeywordsBatched = async (
  memoryBlockIds: string[],
  {
    batchSize = 200,
    signal,
    onProgress,
  }: { batchSize?: number; signal?: AbortSignal; onProgress?: (p: { processed: number; total: number }) => void } = {}
) => {
  const total = memoryBlockIds.length;
  let processed = 0;
  const aggregate: any = {
    suggestions: [],
    successful_count: 0,
    failed_count: 0,
    total_processed: 0,
    message: '',
  };
  for (let i = 0; i < memoryBlockIds.length; i += batchSize) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
    const batch = memoryBlockIds.slice(i, i + batchSize);
    const resp: any = await bulkOperationsService.bulkGenerateKeywords(batch, signal);
    aggregate.suggestions.push(...(resp.suggestions || []));
    aggregate.successful_count += resp.successful_count || 0;
    aggregate.failed_count += resp.failed_count || 0;
    aggregate.total_processed += resp.total_processed || batch.length;
    processed += batch.length;
    onProgress && onProgress({ processed: Math.min(processed, total), total });
  }
  aggregate.message = `Generated keyword suggestions for ${aggregate.successful_count} memory blocks`;
  return aggregate;
};

export const bulkApplyKeywordsBatched = async (
  applications: any[],
  {
    batchSize = 200,
    signal,
    onProgress,
  }: { batchSize?: number; signal?: AbortSignal; onProgress?: (p: { processed: number; total: number }) => void } = {}
) => {
  const total = applications.length;
  let processed = 0;
  const aggregate: any = { results: [], successful_count: 0, failed_count: 0, message: '' };
  for (let i = 0; i < applications.length; i += batchSize) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
    const batch = applications.slice(i, i + batchSize);
    const resp: any = await bulkOperationsService.bulkApplyKeywords(batch, signal);
    aggregate.results.push(...(resp.results || []));
    aggregate.successful_count += resp.successful_count || 0;
    aggregate.failed_count += resp.failed_count || 0;
    processed += batch.length;
    onProgress && onProgress({ processed: Math.min(processed, total), total });
  }
  aggregate.message = `Applied keywords to ${aggregate.successful_count} memory blocks`;
  return aggregate;
};

const bulkOperationsService = {
  bulkCompactMemoryBlocks,
  bulkGenerateKeywords,
  bulkApplyKeywords,
  bulkGenerateKeywordsBatched,
  bulkApplyKeywordsBatched,
};

export default bulkOperationsService;
