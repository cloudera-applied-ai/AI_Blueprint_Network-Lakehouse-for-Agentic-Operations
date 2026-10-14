import { memo } from 'react';
import { X, Network, Gauge, Zap, MapPin, Battery } from 'lucide-react';
import type { Hub } from '@/services/api/coreNetworkApi';

interface HubDetailModalProps {
  hub: Hub;
  onClose: () => void;
}

const statusColors: Record<string, string> = {
  operational: 'text-green-400',
  degraded: 'text-yellow-400',
  failed: 'text-red-400',
  maintenance: 'text-gray-400',
};

const powerColors: Record<string, string> = {
  normal: 'text-green-400',
  battery: 'text-yellow-400',
  generator: 'text-orange-400',
};

const HubDetailModal = memo(({ hub, onClose }: HubDetailModalProps) => {
  const statusClass = statusColors[hub.status.toLowerCase()] || 'text-gray-400';
  const powerClass = powerColors[hub.power_status.toLowerCase()] || 'text-gray-400';

  return (
    <div className="fixed inset-0 bg-black/60 z-[2000] flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-gray-800 border border-gray-700 rounded-xl shadow-2xl w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-teal-600/20 border border-teal-500/40 rounded-lg flex items-center justify-center">
              <Network className="w-4 h-4 text-teal-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">{hub.name}</h2>
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <MapPin className="w-3 h-3" />
                {hub.city}, {hub.state}
              </div>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-700 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {/* Status */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Status</span>
            <span className={`text-sm font-semibold ${statusClass}`}>{hub.status.toUpperCase()}</span>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-3">
            <StatBlock
              icon={<Network className="w-3.5 h-3.5 text-blue-400" />}
              label="Nodes Served"
              value={hub.fiber_nodes_served}
            />
            <StatBlock
              icon={<Gauge className="w-3.5 h-3.5 text-cyan-400" />}
              label="Utilization"
              value={`${hub.utilization_percent}%`}
            />
            <StatBlock
              icon={<Zap className="w-3.5 h-3.5 text-green-400" />}
              label="Throughput"
              value={`${hub.current_throughput_gbps} Gbps`}
            />
            <StatBlock
              icon={<Zap className="w-3.5 h-3.5 text-purple-400" />}
              label="Capacity"
              value={`${hub.fiber_capacity_gbps} Gbps`}
            />
          </div>

          {/* Power */}
          <div className="border-t border-gray-700 pt-4">
            <h3 className="text-xs font-medium text-gray-500 uppercase mb-2">Power</h3>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Battery className="w-3.5 h-3.5 text-gray-400" />
                <span className="text-sm text-gray-300">Power Status</span>
              </div>
              <span className={`text-sm font-medium ${powerClass}`}>{hub.power_status.toUpperCase()}</span>
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-xs text-gray-500">Battery Backup</span>
              <span className="text-xs text-gray-400">{hub.battery_backup_hours} hours</span>
            </div>
          </div>

          {/* Footer */}
          <div className="border-t border-gray-700 pt-4 text-xs text-gray-500">
            ID: {hub.hub_id} &bull; Headend: {hub.headend_id} &bull; Homes: {hub.total_homes_served.toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  );
});

function StatBlock({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="flex items-center gap-2 bg-gray-700/40 rounded-lg px-3 py-2">
      {icon}
      <div>
        <div className="text-xs text-gray-400">{label}</div>
        <div className="text-sm font-medium text-white">{value}</div>
      </div>
    </div>
  );
}

HubDetailModal.displayName = 'HubDetailModal';

export default HubDetailModal;
