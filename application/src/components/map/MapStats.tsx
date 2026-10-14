import { useMemo } from 'react';
import { FiberNode, NodeStatus } from '@/types';
import { Activity, Filter } from 'lucide-react';

export type NodeStatusFilter = 'all' | 'issues' | 'healthy';

interface MapStatsProps {
  nodes: FiberNode[];
  statusFilter?: NodeStatusFilter;
  onFilterChange?: (filter: NodeStatusFilter) => void;
  headendCount?: number;
  hubCount?: number;
}

const MapStats = ({ nodes, statusFilter = 'all', onFilterChange, headendCount = 0, hubCount = 0 }: MapStatsProps) => {
  const stats = useMemo(() => {
    const counts = nodes.reduce((acc, node) => {
      acc[node.status] = (acc[node.status] || 0) + 1;
      return acc;
    }, {} as Record<NodeStatus, number>);

    return {
      total: nodes.length,
      healthy: counts[NodeStatus.HEALTHY] || 0,
      degraded: counts[NodeStatus.DEGRADED] || 0,
      outage: counts[NodeStatus.OUTAGE] || 0,
      maintenance: counts[NodeStatus.MAINTENANCE] || 0,
    };
  }, [nodes]);

  const healthPercentage = ((stats.healthy / stats.total) * 100).toFixed(1);
  const issuesCount = stats.degraded + stats.outage;
  const hasIssues = issuesCount > 0;

  return (
    <div className="absolute top-4 right-4 bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-4 z-[1000]">
      {/* Infrastructure summary */}
      {(headendCount > 0 || hubCount > 0) && (
        <div className="flex items-center gap-3 mb-3 pb-3 border-b border-gray-700 text-xs text-gray-400">
          {headendCount > 0 && (
            <span><span className="text-white font-medium">{headendCount}</span> Headends</span>
          )}
          {hubCount > 0 && (
            <span><span className="text-white font-medium">{hubCount}</span> Hubs</span>
          )}
          <span><span className="text-white font-medium">{stats.total}</span> Nodes</span>
        </div>
      )}

      {/* Filter Controls */}
      {onFilterChange && (
        <div className="flex items-center gap-2 mb-3 pb-3 border-b border-gray-700">
          <span className="text-xs text-gray-400">Filter:</span>
          <div className="flex gap-1">
            <button
              onClick={() => onFilterChange('all')}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                statusFilter === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              All
            </button>
            <button
              onClick={() => onFilterChange('issues')}
              className={`px-2 py-1 text-xs rounded transition-colors flex items-center gap-1 ${
                statusFilter === 'issues'
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <Filter className="w-3 h-3" />
              Issues ({issuesCount})
            </button>
            <button
              onClick={() => onFilterChange('healthy')}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                statusFilter === 'healthy'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Healthy
            </button>
          </div>
        </div>
      )}

      {/* Active Healing Indicator */}
      {hasIssues && (
        <div className="flex items-center gap-2 mb-3 pb-3 border-b border-gray-700">
          <div className="relative">
            <Activity className="w-4 h-4 text-blue-500" />
            <div className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
          </div>
          <span className="text-xs text-blue-400 font-medium">
            Self-healing {issuesCount} node{issuesCount !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      <div className="flex items-center gap-3">
        <div className="text-center">
          <div className="text-2xl font-bold text-white">{stats.total}</div>
          <div className="text-xs text-gray-400">Total Nodes</div>
        </div>
        <div className="h-12 w-px bg-gray-700" />
        <div className="text-center">
          <div className="text-2xl font-bold text-green-500">{healthPercentage}%</div>
          <div className="text-xs text-gray-400">Healthy</div>
        </div>
        <div className="h-12 w-px bg-gray-700" />
        <div className="flex gap-3 text-xs">
          <div className="text-center">
            <div className="font-semibold text-green-500">{stats.healthy}</div>
            <div className="text-gray-400">OK</div>
          </div>
          {stats.degraded > 0 && (
            <div className="text-center">
              <div className="font-semibold text-yellow-500">{stats.degraded}</div>
              <div className="text-gray-400">Degraded</div>
            </div>
          )}
          {stats.outage > 0 && (
            <div className="text-center">
              <div className="font-semibold text-red-500">{stats.outage}</div>
              <div className="text-gray-400">Outage</div>
            </div>
          )}
          {stats.maintenance > 0 && (
            <div className="text-center">
              <div className="font-semibold text-gray-400">{stats.maintenance}</div>
              <div className="text-gray-400">Maint.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MapStats;
