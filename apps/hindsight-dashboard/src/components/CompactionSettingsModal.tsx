import React, { useState } from 'react';
import { createPortal } from 'react-dom';

interface CompactionSuggestion { title: string; description?: string; affected_blocks?: any[]; all_affected_blocks?: any[]; }
interface CompactionSettingsModalProps { isOpen: boolean; onClose: () => void; onConfirm: (params: { count: number; userInstructions: string; maxConcurrent: number }) => void; suggestion: CompactionSuggestion | null; maxBlocks?: number; }

const CompactionSettingsModal: React.FC<CompactionSettingsModalProps> = ({ 
  isOpen, 
  onClose, 
  onConfirm, 
  suggestion,
  maxBlocks = 0
}) => {
  const [selectedCount, setSelectedCount] = useState<number>(Math.min(50, maxBlocks)); // Default to 50 or max available
  const [userInstructions, setUserInstructions] = useState<string>('');
  const [maxConcurrent, setMaxConcurrent] = useState<number>(4); // Default to 4 concurrent processes

  // Debug logging
  console.log('CompactionSettingsModal props:', { 
    isOpen, 
    suggestion, 
    maxBlocks,
    affectedBlocks: suggestion?.affected_blocks?.length,
    allAffectedBlocks: suggestion?.all_affected_blocks?.length
  });

  const handleConfirm = () => {
    onConfirm({
      count: selectedCount,
      userInstructions: userInstructions.trim(),
      maxConcurrent: maxConcurrent
    });
    onClose();
  };

  if (!isOpen || !suggestion) return null;

  return createPortal(
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-2xl shadow-lg rounded-md bg-white">
        <div className="mt-3">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <div>
                <h3 className="text-xl font-semibold text-gray-900">Compaction Settings</h3>
                <p className="text-sm text-gray-600 mt-1">Configure how many memory blocks to process</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Suggestion Info */}
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">{suggestion.title}</h4>
            <p className="text-sm text-blue-700 mb-3">{suggestion.description}</p>
            <div className="text-sm text-blue-600">
              <strong>Total blocks available:</strong> {maxBlocks}
            </div>
          </div>

          {/* Block Count Selection */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of blocks to process
            </label>
            <div className="space-y-3">
              <input
                type="range"
                min="1"
                max={maxBlocks}
                value={selectedCount}
                onChange={(e) => setSelectedCount(parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>1</span>
                <span className="font-medium text-blue-600 text-base">{selectedCount} blocks</span>
                <span>{maxBlocks}</span>
              </div>
            </div>
            
            {/* Quick select buttons */}
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="text-sm text-gray-700">Quick select:</span>
              {[10, 25, 50, 100].filter(num => num <= maxBlocks).map(num => (
                <button
                  key={num}
                  onClick={() => setSelectedCount(num)}
                  className={`px-3 py-1 text-sm rounded border ${
                    selectedCount === num 
                      ? 'bg-blue-600 text-white border-blue-600' 
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {num}
                </button>
              ))}
              {maxBlocks > 100 && (
                <button
                  onClick={() => setSelectedCount(maxBlocks)}
                  className={`px-3 py-1 text-sm rounded border ${
                    selectedCount === maxBlocks 
                      ? 'bg-blue-600 text-white border-blue-600' 
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  All ({maxBlocks})
                </button>
              )}
            </div>
          </div>

          {/* Concurrency Setting */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Concurrent Processes
            </label>
            <div className="space-y-3">
              <input
                type="range"
                min="1"
                max="10"
                value={maxConcurrent}
                onChange={(e) => setMaxConcurrent(parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>1 (Safe)</span>
                <span className="font-medium text-blue-600 text-base">{maxConcurrent} processes</span>
                <span>10 (Fast)</span>
              </div>
            </div>
            
            {/* Quick select buttons for concurrency */}
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="text-sm text-gray-700">Quick select:</span>
              {[1, 2, 4, 6, 8].map(num => (
                <button
                  key={num}
                  onClick={() => setMaxConcurrent(num)}
                  className={`px-3 py-1 text-sm rounded border ${
                    maxConcurrent === num 
                      ? 'bg-blue-600 text-white border-blue-600' 
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {num}
                </button>
              ))}
            </div>
            
            {/* Concurrency Help Text */}
            <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="text-sm text-blue-700">
                <strong>Concurrency Guide:</strong>
                <ul className="mt-2 space-y-1 text-xs">
                  <li>• <strong>1-2 processes:</strong> Safe for most LLM providers, respects rate limits</li>
                  <li>• <strong>3-4 processes:</strong> Good balance of speed and stability (recommended)</li>
                  <li>• <strong>5+ processes:</strong> Faster processing but may hit rate limits</li>
                </ul>
                {maxConcurrent >= 6 && (
                  <p className="mt-2 text-yellow-700 font-medium">
                    ⚠️ High concurrency may cause rate limit errors with some LLM providers
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Cost Warning */}
          <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-yellow-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <div>
                <h4 className="font-medium text-yellow-800">Cost Consideration</h4>
                <p className="text-sm text-yellow-700 mt-1">
                  Compacting memory blocks uses AI processing which incurs costs. Processing {selectedCount} block{selectedCount === 1 ? '' : 's'} will consume API credits.
                  {selectedCount > 50 && (
                    <span className="block mt-1 font-medium">
                      ⚠️ Processing {selectedCount} blocks may take several minutes and consume significant credits.
                    </span>
                  )}
                </p>
              </div>
            </div>
          </div>

          {/* User Instructions */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Additional Instructions (Optional)
            </label>
            <textarea
              value={userInstructions}
              onChange={(e) => setUserInstructions(e.target.value)}
              placeholder="Provide specific instructions for the compaction process..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              Examples: "Focus on technical details", "Preserve user interactions", "Emphasize error patterns"
            </p>
          </div>

          {/* Estimated Processing Time */}
          <div className="mb-6 bg-gray-50 rounded-lg p-3">
            <div className="text-sm text-gray-700">
              <strong>Estimated processing time:</strong> {Math.ceil((selectedCount / maxConcurrent) / 10)} - {Math.ceil((selectedCount / maxConcurrent) / 5)} minutes
            </div>
            <div className="text-sm text-gray-700 mt-1">
              <strong>Processing order:</strong> Largest blocks first (highest compression potential)
            </div>
            <div className="text-sm text-gray-700 mt-1">
              <strong>Concurrency:</strong> Up to {maxConcurrent} block{maxConcurrent === 1 ? '' : 's'} processed simultaneously
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-4 border-t border-gray-200">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              className="px-6 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
            >
              Start Compaction ({selectedCount} block{selectedCount === 1 ? '' : 's'})
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default CompactionSettingsModal;
