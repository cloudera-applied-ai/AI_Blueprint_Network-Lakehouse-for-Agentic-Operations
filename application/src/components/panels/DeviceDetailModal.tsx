import { useState } from 'react';
import { X, Shield, Clock, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import type { NetworkDevice, ConfigChangeLog } from '@/types';

interface Props {
  device: NetworkDevice;
  recentChanges: ConfigChangeLog[];
  complianceHistory: { compliance_id: string; compliance_status: string; severity: string; drift_count: number; scan_timestamp: string }[];
  onClose: () => void;
  onSync: (deviceId: string) => void;
}

const statusColors: Record<string, string> = {
  operational: 'bg-green-500',
  degraded: 'bg-yellow-500',
  offline: 'bg-red-500',
  maintenance: 'bg-blue-500',
};

const complianceColors: Record<string, string> = {
  compliant: 'text-green-400',
  drifted: 'text-yellow-400',
  non_compliant: 'text-red-400',
};

export default function DeviceDetailModal({ device, recentChanges, complianceHistory, onClose, onSync }: Props) {
  const [showConfig, setShowConfig] = useState(false);

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-gray-800 rounded-xl max-w-3xl w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-white">{device.hostname}</h2>
            <p className="text-sm text-gray-400">{device.device_id} &middot; {device.manufacturer} {device.hardware_model}</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => onSync(device.device_id)} className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-md flex items-center gap-1.5">
              <RefreshCw className="w-3.5 h-3.5" /> Sync Config
            </button>
            <button onClick={onClose} className="text-gray-400 hover:text-white"><X className="w-5 h-5" /></button>
          </div>
        </div>

        <div className="p-5 space-y-5">
          {/* Info Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <InfoItem label="Type" value={device.device_type} />
            <InfoItem label="Role" value={device.device_role} />
            <InfoItem label="Status">
              <span className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${statusColors[device.status] || 'bg-gray-500'}`} />
                {device.status}
              </span>
            </InfoItem>
            <InfoItem label="Compliance">
              <span className={complianceColors[device.compliance_status] || 'text-gray-400'}>
                {device.compliance_status}
              </span>
            </InfoItem>
            <InfoItem label="Region" value={device.region || 'N/A'} />
            <InfoItem label="Headend" value={device.headend_id || device.hub_id || 'N/A'} />
            <InfoItem label="Management IP" value={device.management_ip || 'N/A'} />
            <InfoItem label="Firmware" value={device.firmware_version || 'N/A'} />
            <InfoItem label="CPU" value={device.cpu_utilization ? `${device.cpu_utilization}%` : 'N/A'} />
            <InfoItem label="Memory" value={device.memory_utilization ? `${device.memory_utilization}%` : 'N/A'} />
            <InfoItem label="Temp" value={device.temperature_celsius ? `${device.temperature_celsius}°C` : 'N/A'} />
            <InfoItem label="Uplink" value={device.uplink_speed_gbps ? `${device.uplink_speed_gbps} Gbps` : 'N/A'} />
          </div>

          {/* Running Config (collapsible) */}
          <div className="border border-gray-700 rounded-lg">
            <button onClick={() => setShowConfig(!showConfig)} className="w-full flex items-center justify-between px-4 py-3 text-sm text-gray-300 hover:bg-gray-700/50">
              <span className="flex items-center gap-2"><Shield className="w-4 h-4" /> Running Configuration</span>
              {showConfig ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
            {showConfig && (
              <pre className="px-4 pb-3 text-xs text-gray-400 overflow-x-auto max-h-60">
                {JSON.stringify(device.running_config, null, 2)}
              </pre>
            )}
          </div>

          {/* Recent Changes */}
          <div>
            <h3 className="text-sm font-medium text-gray-300 mb-2 flex items-center gap-2">
              <Clock className="w-4 h-4" /> Recent Changes ({recentChanges.length})
            </h3>
            {recentChanges.length === 0 ? (
              <p className="text-sm text-gray-500">No recent changes</p>
            ) : (
              <div className="space-y-2">
                {recentChanges.map(c => (
                  <div key={c.change_id} className="bg-gray-700/50 rounded-lg p-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-300">{c.change_description || c.change_type}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${c.status === 'applied' ? 'bg-green-500/20 text-green-400' : c.status === 'rolled_back' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-gray-500/20 text-gray-400'}`}>
                        {c.status}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {c.change_timestamp} &middot; by {c.applied_by || 'system'}
                      {c.rollback_available && <span className="ml-2 text-blue-400">rollback available</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Compliance History */}
          {complianceHistory.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-300 mb-2">Compliance History</h3>
              <div className="space-y-1">
                {complianceHistory.map(c => (
                  <div key={c.compliance_id} className="flex items-center justify-between text-sm bg-gray-700/30 rounded px-3 py-2">
                    <span className={complianceColors[c.compliance_status] || 'text-gray-400'}>{c.compliance_status}</span>
                    <span className="text-gray-500 text-xs">{c.drift_count} drifts &middot; {c.scan_timestamp}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function InfoItem({ label, value, children }: { label: string; value?: string; children?: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm text-gray-200">{children || value || 'N/A'}</p>
    </div>
  );
}
