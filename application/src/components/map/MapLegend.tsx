import { useMemo } from 'react';
import { NodeStatus, FiberNode } from '@/types';
import { getMarkerColor } from '@/utils/helpers';

interface MapLegendProps {
  nodes?: FiberNode[];
  headendCount?: number;
  hubCount?: number;
}

const MapLegend = ({ nodes, headendCount = 0, hubCount = 0 }: MapLegendProps) => {
  const stats = useMemo(() => {
    if (!nodes) return null;

    const counts = nodes.reduce((acc, node) => {
      acc[node.status] = (acc[node.status] || 0) + 1;
      return acc;
    }, {} as Record<NodeStatus, number>);

    const total = nodes.length;
    return {
      total,
      items: [
        {
          status: NodeStatus.HEALTHY,
          label: 'Healthy',
          count: counts[NodeStatus.HEALTHY] || 0,
          percentage: ((counts[NodeStatus.HEALTHY] || 0) / total) * 100,
        },
        {
          status: NodeStatus.DEGRADED,
          label: 'Degraded',
          count: counts[NodeStatus.DEGRADED] || 0,
          percentage: ((counts[NodeStatus.DEGRADED] || 0) / total) * 100,
        },
        {
          status: NodeStatus.OUTAGE,
          label: 'Outage',
          count: counts[NodeStatus.OUTAGE] || 0,
          percentage: ((counts[NodeStatus.OUTAGE] || 0) / total) * 100,
        },
        {
          status: NodeStatus.MAINTENANCE,
          label: 'Maintenance',
          count: counts[NodeStatus.MAINTENANCE] || 0,
          percentage: ((counts[NodeStatus.MAINTENANCE] || 0) / total) * 100,
        },
      ],
    };
  }, [nodes]);

  const legendItems = stats?.items || [
    { status: NodeStatus.HEALTHY, label: 'Healthy', count: 0, percentage: 0 },
    { status: NodeStatus.DEGRADED, label: 'Degraded', count: 0, percentage: 0 },
    { status: NodeStatus.OUTAGE, label: 'Outage', count: 0, percentage: 0 },
    { status: NodeStatus.MAINTENANCE, label: 'Maintenance', count: 0, percentage: 0 },
  ];

  const showInfra = headendCount > 0 || hubCount > 0;

  return (
    <div className="absolute bottom-6 right-6 bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-4 z-[1000]">
      {/* Infrastructure marker types */}
      {showInfra && (
        <>
          <h3 className="text-sm font-semibold text-gray-200 mb-2">Infrastructure</h3>
          <div className="space-y-1.5 mb-3 pb-3 border-b border-gray-700">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-emerald-500 border-2 border-white rounded-sm flex-shrink-0" />
              <span className="text-xs text-gray-300">Headend / CO</span>
              <span className="text-xs text-gray-500 ml-auto">{headendCount}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3.5 h-3.5 bg-emerald-500 border border-white rounded-sm flex-shrink-0"
                style={{ transform: 'rotate(45deg)' }}
              />
              <span className="text-xs text-gray-300 ml-0.5">Hub</span>
              <span className="text-xs text-gray-500 ml-auto">{hubCount}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-emerald-500 rounded-full border border-white flex-shrink-0 ml-0.5" />
              <span className="text-xs text-gray-300 ml-0.5">Fiber Node</span>
            </div>
          </div>
        </>
      )}

      <h3 className="text-sm font-semibold text-gray-200 mb-3">Node Status</h3>
      <div className="space-y-2">
        {legendItems.map(({ status, label, count, percentage }) => (
          <div key={status} className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 flex-1">
              <div
                className="w-4 h-4 rounded-full border-2 border-gray-700 flex-shrink-0"
                style={{ backgroundColor: getMarkerColor(status) }}
              />
              <span className="text-sm text-gray-300">{label}</span>
            </div>
            {stats && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-400 font-medium">{count}</span>
                <span className="text-gray-600">({percentage.toFixed(1)}%)</span>
              </div>
            )}
          </div>
        ))}
      </div>
      {stats && (
        <div className="mt-3 pt-3 border-t border-gray-700 text-xs text-gray-500">
          Click any marker to view details
        </div>
      )}
    </div>
  );
};

export default MapLegend;
