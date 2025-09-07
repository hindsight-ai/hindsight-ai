import memoryService from '../memoryService';

jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: { show401Error: jest.fn(), showWarning: jest.fn() },
}));

describe('memoryService 401 branches', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 401 });
  });

  const expectAuthRequired = async (fn) => {
    await expect(fn()).rejects.toThrow('Authentication required');
  };

  test('401 on endpoints triggers auth error', async () => {
    const m = memoryService;
    await expectAuthRequired(() => m.getMemoryBlocks({}));
    await expectAuthRequired(() => m.getMemoryBlockById('mb'));
    await expectAuthRequired(() => m.updateMemoryBlock('mb', { a: 1 }));
    await expectAuthRequired(() => m.archiveMemoryBlock('mb'));
    await expectAuthRequired(() => m.deleteMemoryBlock('mb'));
    await expectAuthRequired(() => m.getArchivedMemoryBlocks({}));
    await expectAuthRequired(() => m.getKeywords());
    await expectAuthRequired(() => m.createKeyword({ keyword_text: 'x' }));
    await expectAuthRequired(() => m.updateKeyword('k', { keyword_text: 'y' }));
    await expectAuthRequired(() => m.deleteKeyword('k'));
    await expectAuthRequired(() => m.getKeywordMemoryBlocks('k', 0, 10));
    await expectAuthRequired(() => m.getKeywordMemoryBlocksCount('k'));
    await expectAuthRequired(() => m.addKeywordToMemoryBlock('mb', 'k'));
    await expectAuthRequired(() => m.removeKeywordFromMemoryBlock('mb', 'k'));
    await expectAuthRequired(() => m.getConsolidationSuggestions({}));
    await expectAuthRequired(() => m.getConsolidationSuggestionById('s'));
    await expectAuthRequired(() => m.validateConsolidationSuggestion('s'));
    await expectAuthRequired(() => m.rejectConsolidationSuggestion('s'));
    await expectAuthRequired(() => m.triggerConsolidation());
    await expectAuthRequired(() => m.deleteConsolidationSuggestion('s'));
    await expectAuthRequired(() => m.generatePruningSuggestions({}));
    await expectAuthRequired(() => m.confirmPruning([]));
    await expectAuthRequired(() => m.getBuildInfo());
    await expectAuthRequired(() => m.getConversationsCount());
    await expectAuthRequired(() => m.suggestKeywords('mb'));
    await expectAuthRequired(() => m.compressMemoryBlock('mb', {}));
    await expectAuthRequired(() => m.applyMemoryCompression('mb', {}));
    await expectAuthRequired(() => m.getMemoryOptimizationSuggestions({}));
    await expectAuthRequired(() => m.executeOptimizationSuggestion('s'));
    await expectAuthRequired(() => m.getSuggestionDetails('s'));
    await expectAuthRequired(() => m.bulkCompactMemoryBlocks(['mb']));
    await expectAuthRequired(() => m.bulkGenerateKeywords(['mb']));
    await expectAuthRequired(() => m.bulkApplyKeywords([{ memory_block_id: 'mb', keywords: ['x'] }]));
    await expectAuthRequired(() => m.mergeMemoryBlocks(['mb'], 'content'));
  });
});

