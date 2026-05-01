// Re-aggregation facade — backward-compat default export for consumers that do
// `import memoryService from '../api/memoryService'`.
// Named types re-exported for consumers that import them by name from this module.
import memoryBlocksService from './memoryBlocksService';
import keywordsService from './keywordsService';
import consolidationService from './consolidationService';
import pruningService from './pruningService';
import compressionService from './compressionService';
import memoryOptimizationService from './memoryOptimizationService';
import bulkOperationsService from './bulkOperationsService';
import supportService from './supportService';
import metaService from './metaService';

export type { MemoryBlock } from './memoryBlocksService';
export type { Keyword } from './keywordsService';
export type { ConsolidationSuggestion } from './consolidationService';

const memoryService = {
  ...memoryBlocksService,
  ...keywordsService,
  ...consolidationService,
  ...pruningService,
  ...compressionService,
  ...memoryOptimizationService,
  ...bulkOperationsService,
  ...supportService,
  ...metaService,
};

export default memoryService;
