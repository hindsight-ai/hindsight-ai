import React, { useState } from 'react';
import memoryService, { MemoryBlock } from '../api/memoryService';
import { UIMemoryBlock } from '../types/domain';

export interface MemoryCompactionResult {
  compression_ratio: number;
  compression_quality_score: number;
  original_content?: string;
  original_lessons_learned?: string;
  compressed_content?: string;
  compressed_lessons_learned?: string;
  key_insights_preserved?: string[];
  rationale?: string;
}

interface MemoryCompactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  memoryBlock: (MemoryBlock & UIMemoryBlock) | null;
  onCompactionApplied?: (id: string, result: MemoryCompactionResult) => void;
}

const MemoryCompactionModal: React.FC<MemoryCompactionModalProps> = ({
  isOpen,
  onClose,
  memoryBlock,
  onCompactionApplied
}) => {
  const [compactionResult, setCompactionResult] = useState<MemoryCompactionResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [userInstructions, setUserInstructions] = useState<string>('');
  const [applying, setApplying] = useState<boolean>(false);

  const handleCompact = async () => {
    if (!memoryBlock) return;

    setLoading(true);
    setError(null);

    try {
      const result: MemoryCompactionResult = await memoryService.compressMemoryBlock(
        memoryBlock!.id,
        { user_instructions: userInstructions }
      );
      setCompactionResult(result);
    } catch (err) {
  setError((err as any)?.message || 'Failed to compact memory block');
    } finally {
      setLoading(false);
    }
  };

  const handleApplyCompaction = async () => {
    if (!compactionResult) return;

    setApplying(true);
    try {
      await memoryService.applyMemoryCompression(
        memoryBlock!.id,
        {
          compressed_content: compactionResult.compressed_content,
          compressed_lessons_learned: compactionResult.compressed_lessons_learned
        }
      );

      // Notify parent component
  onCompactionApplied?.(memoryBlock!.id, compactionResult);

      onClose();
    } catch (err) {
      setError((err as any)?.message || 'Failed to apply compaction');
    } finally {
      setApplying(false);
    }
  };

  const handleRetry = () => {
    setCompactionResult(null);
    setError(null);
    setUserInstructions('');
  };

  const handleRefine = () => {
    setCompactionResult(null);
    setError(null);
    // Keep the user instructions for refinement
  };

  if (!isOpen || !memoryBlock) return null;

  const compactionRatio = compactionResult ?
    Math.round((1 - compactionResult.compression_ratio) * 100) : 0;

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div 
        className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-800">AI Memory Compaction</h2>
            <p className="text-sm text-gray-600 mt-1">
              Intelligently condense and optimize memory content while preserving key insights
            </p>
            <p className="text-xs text-gray-500 mt-1">
              ID: {memoryBlock.id.slice(-8)} • Agent: {memoryBlock.agent_id.slice(-8)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {!compactionResult ? (
            /* Initial State - Show original content and compaction options */
            <div className="space-y-6">
              {/* Original Content */}
              <div>
                <h3 className="text-lg font-medium text-gray-800 mb-3">Current Memory Content</h3>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 max-h-64 overflow-y-auto">
                  <div className="space-y-4">
                    {memoryBlock.content && (
                      <div>
                        <h4 className="font-medium text-gray-700 mb-2">Content:</h4>
                        <p className="text-sm text-gray-600 whitespace-pre-wrap">
                          {memoryBlock.content}
                        </p>
                      </div>
                    )}
                    {memoryBlock.lessons_learned && (
                      <div>
                        <h4 className="font-medium text-gray-700 mb-2">Lessons Learned:</h4>
                        <p className="text-sm text-gray-600 whitespace-pre-wrap">
                          {memoryBlock.lessons_learned}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
                <div className="mt-2 text-sm text-gray-500">
                  Current length: {memoryBlock.content?.length || 0} characters
                </div>
              </div>

              {/* Compaction Instructions */}
              <div>
                <h3 className="text-lg font-medium text-gray-800 mb-3">
                  Compaction Instructions (Optional)
                </h3>
                <p className="text-sm text-gray-600 mb-3">
                  Guide the AI on how to condense this memory while preserving what matters most.
                </p>
                <textarea
                  value={userInstructions}
                  onChange={(e) => setUserInstructions(e.target.value)}
                  placeholder="e.g., 'Preserve technical details and error codes', 'Focus on outcomes and learnings', 'Keep specific numbers and metrics'..."
                  className="w-full h-24 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                />
              </div>

              {/* Error Display */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-center">
                    <svg className="w-5 h-5 text-red-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    <p className="text-red-700">{error}</p>
                  </div>
                </div>
              )}

              {/* Compact Button */}
              <div className="flex justify-center">
                <button
                  onClick={handleCompact}
                  disabled={loading}
                  className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center"
                >
                  {loading ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Analyzing & Compacting...
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Generate Compacted Version
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : (
            /* Compaction Result - Show comparison */
            <div className="space-y-6">
              {/* Compaction Stats */}
              <div className="bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-green-800">✨ Memory Successfully Compacted</h3>
                    <p className="text-sm text-green-700 mt-1">
                      Space saved: {compactionRatio}% • Information density improved • Quality preserved: {compactionResult.compression_quality_score}/10
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-green-600">{compactionRatio}%</div>
                    <div className="text-sm text-green-600">more efficient</div>
                  </div>
                </div>
              </div>

              {/* Side-by-side comparison */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Original */}
                <div>
                  <h3 className="text-lg font-medium text-gray-800 mb-3 flex items-center">
                    <span className="w-3 h-3 bg-orange-500 rounded-full mr-2"></span>
                    Current Version
                  </h3>
                  <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 max-h-96 overflow-y-auto">
                    <div className="space-y-4">
                      {compactionResult.original_content && (
                        <div>
                          <h4 className="font-medium text-orange-700 mb-2">Content:</h4>
                          <p className="text-sm text-orange-600 whitespace-pre-wrap">
                            {compactionResult.original_content}
                          </p>
                        </div>
                      )}
                      {compactionResult.original_lessons_learned && (
                        <div>
                          <h4 className="font-medium text-orange-700 mb-2">Lessons Learned:</h4>
                          <p className="text-sm text-orange-600 whitespace-pre-wrap">
                            {compactionResult.original_lessons_learned}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Compacted */}
                <div>
                  <h3 className="text-lg font-medium text-gray-800 mb-3 flex items-center">
                    <span className="w-3 h-3 bg-green-500 rounded-full mr-2"></span>
                    Compacted Version
                  </h3>
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4 max-h-96 overflow-y-auto">
                    <div className="space-y-4">
                      {compactionResult.compressed_content && (
                        <div>
                          <h4 className="font-medium text-green-700 mb-2">Content:</h4>
                          <p className="text-sm text-green-600 whitespace-pre-wrap">
                            {compactionResult.compressed_content}
                          </p>
                        </div>
                      )}
                      {compactionResult.compressed_lessons_learned && (
                        <div>
                          <h4 className="font-medium text-green-700 mb-2">Lessons Learned:</h4>
                          <p className="text-sm text-green-600 whitespace-pre-wrap">
                            {compactionResult.compressed_lessons_learned}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Key Insights */}
              {compactionResult.key_insights_preserved && compactionResult.key_insights_preserved.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium text-gray-800 mb-3">Key Insights Preserved</h3>
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <ul className="list-disc list-inside space-y-1">
                      {compactionResult.key_insights_preserved.map((insight, index) => (
                        <li key={index} className="text-sm text-yellow-800">{insight}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Rationale */}
              {compactionResult.rationale && (
                <div>
                  <h3 className="text-lg font-medium text-gray-800 mb-3">AI Compaction Strategy</h3>
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-sm text-blue-800">{compactionResult.rationale}</p>
                  </div>
                </div>
              )}

              {/* Error Display */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-center">
                    <svg className="w-5 h-5 text-red-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    <p className="text-red-700">{error}</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
          {!compactionResult ? (
            /* Initial state buttons */
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
            </>
          ) : (
            /* Result state buttons */
            <>
              <button
                onClick={handleRetry}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                disabled={applying}
              >
                Start Over
              </button>
              <button
                onClick={handleRefine}
                className="px-4 py-2 text-blue-600 hover:text-blue-800 transition-colors"
                disabled={applying}
              >
                Refine Further
              </button>
              <button
                onClick={handleApplyCompaction}
                disabled={applying}
                className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center"
              >
                {applying ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Applying Compaction...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                    </svg>
                    Apply Compacted Version
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default MemoryCompactionModal;
