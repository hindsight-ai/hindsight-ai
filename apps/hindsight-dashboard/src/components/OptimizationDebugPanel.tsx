import React, { FC, useState } from 'react';
import memoryService from '../api/memoryService';
import type { MemoryBlock } from '../api/memoryService';
import type { Suggestion } from '../hooks/useMemoryOptimization';

interface DebugBlockResult {
  success: boolean;
  data?: {
    id: string;
    agent_id: string;
    content_preview: string;
  };
  error?: string;
}

interface OptimizationDebugPanelProps {
  suggestions: Suggestion[];
  onClose: () => void;
}

const OptimizationDebugPanel: FC<OptimizationDebugPanelProps> = ({ suggestions, onClose }) => {
  const [debugBlockId, setDebugBlockId] = useState<string>('');
  const [debugLoading, setDebugLoading] = useState<boolean>(false);
  const [debugBlockResult, setDebugBlockResult] = useState<DebugBlockResult | null>(null);

  const testBlockId = async (blockId: string) => {
    if (!blockId.trim()) return;

    setDebugLoading(true);
    setDebugBlockResult(null);

    try {
      console.log('Testing block ID:', blockId);
      const blockData: MemoryBlock = await memoryService.getMemoryBlockById(blockId);
      setDebugBlockResult({
        success: true,
        data: {
          id: blockData.id,
          agent_id: blockData.agent_id,
          content_preview: (blockData.content || '').slice(0, 100) + '...',
        },
      });
    } catch (error: any) {
      console.error('Block test failed:', error);
      setDebugBlockResult({
        success: false,
        error: error.message,
      });
    } finally {
      setDebugLoading(false);
    }
  };

  return (
    <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-yellow-800">🔧 Debug Panel</h3>
        <button onClick={onClose} className="text-yellow-600 hover:text-yellow-800">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="space-y-4">
        {/* Suggestion Info */}
        <div>
          <h4 className="font-medium text-yellow-800 mb-2">Current Suggestions Analysis:</h4>
          <div className="bg-white rounded border p-3 text-sm">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <strong>Total Suggestions:</strong> {suggestions.length}
              </div>
              <div>
                <strong>Total Affected Blocks:</strong>{' '}
                {suggestions.reduce((sum, s) => sum + (s.affected_blocks?.length || 0), 0)}
              </div>
            </div>
            <div className="mt-2">
              <strong>Suggestion Types:</strong>{' '}
              {[...new Set(suggestions.map(s => s.type))].join(', ') || 'None'}
            </div>
          </div>
        </div>

        {/* Block ID Tester */}
        <div>
          <h4 className="font-medium text-yellow-800 mb-2">Test Block ID:</h4>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              value={debugBlockId}
              onChange={e => setDebugBlockId(e.target.value)}
              placeholder="Enter block ID to test..."
              className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-yellow-500 focus:ring-yellow-500 sm:text-sm"
            />
            <button
              onClick={() => testBlockId(debugBlockId)}
              disabled={debugLoading || !debugBlockId.trim()}
              className="bg-yellow-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-yellow-700 disabled:opacity-50"
            >
              {debugLoading ? 'Testing...' : 'Test'}
            </button>
          </div>

          {/* Quick test buttons for blocks from suggestions */}
          {suggestions.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2">
              <span className="text-sm text-yellow-700">Quick test:</span>
              {suggestions.slice(0, 2).map((suggestion, i) =>
                suggestion.affected_blocks?.slice(0, 2).map((blockId, j) => (
                  <button
                    key={`${i}-${j}`}
                    onClick={() => {
                      setDebugBlockId(blockId);
                      testBlockId(blockId);
                    }}
                    className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded border hover:bg-yellow-200"
                  >
                    {blockId.slice(0, 8)}...
                  </button>
                ))
              )}
            </div>
          )}

          {/* Test Result */}
          {debugBlockResult && (
            <div
              className={`p-3 rounded border ${
                debugBlockResult.success
                  ? 'bg-green-50 border-green-200 text-green-800'
                  : 'bg-red-50 border-red-200 text-red-800'
              }`}
            >
              {debugBlockResult.success ? (
                <div>
                  <div className="font-medium mb-2">✅ Block Found!</div>
                  <div className="text-sm space-y-1">
                    {debugBlockResult.data && (
                      <>
                        <div>
                          <strong>ID:</strong> {debugBlockResult.data.id}
                        </div>
                        <div>
                          <strong>Agent:</strong> {debugBlockResult.data.agent_id || 'None'}
                        </div>
                        <div>
                          <strong>Content Preview:</strong> {debugBlockResult.data.content_preview}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ) : (
                <div>
                  <div className="font-medium mb-2">❌ Block Not Found</div>
                  <div className="text-sm">{debugBlockResult.error}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OptimizationDebugPanel;
