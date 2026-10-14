import { memo } from 'react';
import { X, Server, Users, Gauge, Zap, MapPin } from 'lucide-react';
import type { Headend } from '@/services/api/coreNetworkApi';

interface HeadendDetailModalProps {
  headend: Headend;
  onClose: () => void;
}

const statusColors: Record<string, string> = {
  operational: 'text-green-400',
  degraded: 'text-yellow-400',
  failed: 'text-red-400',
  maintenance: 'text-gray-400',
};

const HeadendDetailModal = memo(({ headend, onClose }: HeadendDetailModalProps) => {
  const he = headend;
  const statusClass = statusColors[he.status.toLowerCase()] || 'text-gray-400';

  return (
    <div className="fixed inset-0 bg-black/60 z-[2000] flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-gray-800 border border-gray-700 rounded-xl shadow-2xl w-full max-w-lg"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600/20 border border-blue-500/40 rounded-lg flex items-center justify-center">
              <Server className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">{he.name}</h2>
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <MapPin className="w-3 h-3" />
                {he.city}, {he.state} &bull; {he.region}
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
            <span className={`text-sm font-semibold ${statusClass}`}>{he.status.toUpperCase()}</span>
          </div>

          {/* Infrastructure */}
          <div className="grid grid-cols-2 gap-3">
            <Stat icon={<Server className="w-3.5 h-3.5 text-blue-400" />} label="CMTS Devices" value={he.cmts_count} />
            <Stat icon={<Gauge className="w-3.5 h-3.5 text-cyan-400" />} label="Port Utilization" value={`${he.port_utilization_percent}%`} />
            <Stat icon={<Users className="w-3.5 h-3.5 text-green-400" />} label="Subscribers" value={he.total_active_subscribers.toLocaleString()} />
            <Stat icon={<Users className="w-3.5 h-3.5 text-purple-400" />} label="Homes Served" value={he.total_homes_served.toLocaleString()} />
            <Stat icon={<Zap className="w-3.5 h-3.5 text-yellow-400" />} label="Peering Capacity" value={`${he.peering_capacity_gbps} Gbps`} />
            <Stat icon={<Zap className="w-3.5 h-3.5 text-orange-400" />} label="Power Capacity" value={`${he.power_capacity_mw} MW`} />
          </div>

          {/* Equipment */}
          <div className="border-t border-gray-700 pt-4">
            <h3 className="text-xs font-medium text-gray-500 uppercase mb-2">Equipment</h3>
            <div className="grid grid-cols-3 gap-3">
              <MiniStat label="CMTS Ports" value={`${he.active_cmts_ports} / ${he.total_cmts_ports}`} />
              <MiniStat label="Video Servers" value={he.video_server_count} />
              <MiniStat label="Core Routers" value={he.core_router_count} />
            </div>
          </div>

          {/* Location */}
          <div className="border-t border-gray-700 pt-4 text-xs text-gray-500">
            ID: {he.headend_id} &bull; Service Area: {he.service_area} &bull; {he.total_rack_units} rack units
          </div>
        </div>
      </div>
    </div>
  );
});

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
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

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="text-center">
      <div className="text-sm font-medium text-white">{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

HeadendDetailModal.displayName = 'HeadendDetailModal';

export default HeadendDetailModal;
