import memoryService from '../memoryService';

describe('memoryService non-401 error branches', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 });
  });

  const expectReject = async (fn) => {
    await expect(fn()).rejects.toThrow('HTTP error');
  };

  test('errors on various endpoints', async () => {
    const m = memoryService;
    await expectReject(() => m.getMemoryBlocks({}));
    await expectReject(() => m.getMemoryBlockById('mb'));
    await expectReject(() => m.updateMemoryBlock('mb', { a: 1 }));
    await expectReject(() => m.archiveMemoryBlock('mb'));
    await expectReject(() => m.deleteMemoryBlock('mb'));
    await expectReject(() => m.getArchivedMemoryBlocks({}));
    await expectReject(() => m.getKeywords());
    await expectReject(() => m.createKeyword({ keyword_text: 'x' }));
    await expectReject(() => m.updateKeyword('k', { keyword_text: 'y' }));
    await expectReject(() => m.deleteKeyword('k'));
    await expectReject(() => m.getKeywordMemoryBlocks('k', 0, 10));
    await expectReject(() => m.getKeywordMemoryBlocksCount('k'));
    await expectReject(() => m.addKeywordToMemoryBlock('mb', 'k'));
    await expectReject(() => m.removeKeywordFromMemoryBlock('mb', 'k'));
    await expectReject(() => m.getConsolidationSuggestions({}));
    await expectReject(() => m.getConsolidationSuggestionById('s'));
    await expectReject(() => m.validateConsolidationSuggestion('s'));
    await expectReject(() => m.rejectConsolidationSuggestion('s'));
    await expectReject(() => m.triggerConsolidation());
    await expectReject(() => m.deleteConsolidationSuggestion('s'));
    await expectReject(() => m.generatePruningSuggestions({}));
    await expectReject(() => m.confirmPruning([]));
    await expectReject(() => m.getBuildInfo());
    await expectReject(() => m.getConversationsCount());
    await expectReject(() => m.suggestKeywords('mb'));
    await expectReject(() => m.compressMemoryBlock('mb', {}));
    await expectReject(() => m.applyMemoryCompression('mb', {}));
    await expectReject(() => m.getMemoryOptimizationSuggestions({}));
    await expectReject(() => m.executeOptimizationSuggestion('s'));
    await expectReject(() => m.getSuggestionDetails('s'));
    await expectReject(() => m.bulkCompactMemoryBlocks(['mb']));
    await expectReject(() => m.bulkGenerateKeywords(['mb']));
    await expectReject(() => m.bulkApplyKeywords([{ memory_block_id: 'mb', keywords: ['x'] }]));
    await expectReject(() => m.mergeMemoryBlocks(['mb'], 'content'));
  });
});
