import React, { FC } from 'react';
import type { Filters } from '../hooks/useMemoryOptimization';
import type { Agent } from '../api/agentService';

interface OptimizationFiltersProps {
  filters: Filters;
  availableAgents: Agent[];
  onFilterChange: (filterType: keyof Filters, value: string) => void;
  onClearFilters: () => void;
}

const OptimizationFilters: FC<OptimizationFiltersProps> = ({
  filters,
  availableAgents,
  onFilterChange,
  onClearFilters,
}) => {
  return (
    <div className="mt-6 bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">Filters</h3>
        <button
          onClick={onClearFilters}
          className="text-blue-600 hover:text-blue-800 text-sm font-medium"
        >
          Clear All
        </button>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Agent Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Agent ID</label>
          <select
            value={filters.agentId}
            onChange={e => onFilterChange('agentId', e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            <option key="all-agents" value="">All Agents</option>
            {availableAgents.map((agent, index) => (
              <option key={agent.agent_id || `agent-${index}`} value={agent.agent_id}>
                {agent.agent_name || 'Unnamed Agent'}
              </option>
            ))}
          </select>
        </div>

        {/* Priority Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
          <select
            value={filters.priority}
            onChange={e => onFilterChange('priority', e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            <option key="all-priorities" value="">All Priorities</option>
            <option key="high" value="high">High Priority</option>
            <option key="medium" value="medium">Medium Priority</option>
            <option key="low" value="low">Low Priority</option>
          </select>
        </div>

        {/* Date Range Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Date Range</label>
          <select
            value={filters.dateRange}
            onChange={e => onFilterChange('dateRange', e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            <option key="all-time" value="">All Time</option>
            <option key="last_7_days" value="last_7_days">Last 7 Days</option>
            <option key="last_30_days" value="last_30_days">Last 30 Days</option>
            <option key="last_90_days" value="last_90_days">Last 90 Days</option>
          </select>
        </div>
      </div>
    </div>
  );
};

export default OptimizationFilters;
