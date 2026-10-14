import { useState, useEffect, useCallback } from 'react';
import { Server, Shield, GitPullRequest, Activity, RefreshCw, Search } from 'lucide-react';
import {
  getDeviceSummary,
  getDevices,
  getDeviceDetail,
  syncDevice,
  getComplianceSummary,
  triggerComplianceScan,
  getChangeRequests,
  updateChangeRequest,
  executeChangeRequest,
  getChanges,
} from '@/services/api/configManagementApi';
import type {
  NetworkDevice,
  DeviceSummary,
  ComplianceSummary,
  ChangeRequest,
  ConfigChangeLog,
} from '@/types';
import DeviceDetailModal from '@/components/panels/DeviceDetailModal';
import ComplianceOverview from '@/components/panels/ComplianceOverview';
import ChangeRequestPanel from '@/components/panels/ChangeRequestPanel';
import AgentActivityFeed from '@/components/panels/AgentActivityFeed';

const deviceTypeColors: Record<string, string> = {
  firewall: 'bg-red-500/20 text-red-400 border-red-500/30',
  switch: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  router: 'bg-green-500/20 text-green-400 border-green-500/30',
  modem: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
};

const deviceTypeIcons: Record<string, string> = {
  firewall: '🛡️',
  switch: '🔀',
  router: '🌐',
  modem: '📡',
};

export default function ConfigManagementView() {
  const [summary, setSummary] = useState<DeviceSummary | null>(null);
  const [devices, setDevices] = useState<NetworkDevice[]>([]);
  const [totalDevices, setTotalDevices] = useState(0);
  const [complianceSummary, setComplianceSummary] = useState<ComplianceSummary | null>(null);
  const [changeRequests, setChangeRequests] = useState<ChangeRequest[]>([]);
  const [recentChanges, setRecentChanges] = useState<ConfigChangeLog[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<{
    device: NetworkDevice;
    recent_changes: ConfigChangeLog[];
    compliance_history: { compliance_id: string; compliance_status: string; severity: string; drift_count: number; scan_timestamp: string }[];
  } | null>(null);

  const [filterType, setFilterType] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [summaryData, devicesData, compData, crData, changesData] = await Promise.all([
        getDeviceSummary(),
        getDevices({ device_type: filterType || undefined, status: filterStatus || undefined, limit: 100 }),
        getComplianceSummary(),
        getChangeRequests({ limit: 20 }),
        getChanges({ limit: 20 }),
      ]);
      setSummary(summaryData);
      setDevices(devicesData.devices);
      setTotalDevices(devicesData.total);
      setComplianceSummary(compData);
      setChangeRequests(crData.requests);
      setRecentChanges(changesData.changes);
    } catch (err) {
      console.error('Failed to fetch config management data:', err);
    } finally {
      setLoading(false);
    }
  }, [filterType, filterStatus]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleDeviceClick = async (device: NetworkDevice) => {
    try {
      const detail = await getDeviceDetail(device.device_id);
      setSelectedDevice(detail);
    } catch (err) {
      console.error('Failed to fetch device detail:', err);
    }
  };

  const handleSync = async (deviceId: string) => {
    try {
      await syncDevice(deviceId);
      await fetchData();
      if (selectedDevice?.device.device_id === deviceId) {
        const detail = await getDeviceDetail(deviceId);
        setSelectedDevice(detail);
      }
    } catch (err) {
      console.error('Sync failed:', err);
    }
  };

  const handleComplianceScan = async () => {
    setScanning(true);
    try {
      await triggerComplianceScan();
      await fetchData();
    } catch (err) {
      console.error('Compliance scan failed:', err);
    } finally {
      setScanning(false);
    }
  };

  const handleApprove = async (requestId: string) => {
    setActionLoading(true);
    try {
      await updateChangeRequest(requestId, { status: 'approved', approved_by: 'admin' });
      await fetchData();
    } catch (err) {
      console.error('Approve failed:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (requestId: string) => {
    setActionLoading(true);
    try {
      await updateChangeRequest(requestId, { status: 'rejected', reviewed_by: 'admin' });
      await fetchData();
    } catch (err) {
      console.error('Reject failed:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleExecute = async (requestId: string) => {
    setActionLoading(true);
    try {
      await executeChangeRequest(requestId);
      await fetchData();
    } catch (err) {
      console.error('Execute failed:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const filteredDevices = searchQuery
    ? devices.filter(d =>
        d.hostname.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.device_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.manufacturer?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.management_ip?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : devices;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
        <span className="ml-2 text-gray-400">Loading configuration data...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <SummaryCard icon={<Server className="w-5 h-5 text-blue-400" />} label="Total Devices" value={summary?.total_devices || 0} />
        {Object.entries(summary?.by_type || {}).map(([type, count]) => (
          <SummaryCard key={type} icon={<span className="text-lg">{deviceTypeIcons[type] || '📦'}</span>} label={type.charAt(0).toUpperCase() + type.slice(1) + 's'} value={count} />
        ))}
        <SummaryCard icon={<Shield className="w-5 h-5 text-green-400" />} label="Compliance" value={`${summary?.compliance_rate || 100}%`} />
        <SummaryCard icon={<Activity className="w-5 h-5 text-yellow-400" />} label="Config Drifts" value={summary?.drift_count || 0} />
        <SummaryCard icon={<GitPullRequest className="w-5 h-5 text-purple-400" />} label="Recent Changes" value={summary?.recent_changes || 0} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Device Inventory - takes 2 cols */}
        <div className="lg:col-span-2 bg-gray-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
              <Server className="w-4 h-4" /> Device Inventory ({totalDevices})
            </h3>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-2.5 top-2 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search devices..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="bg-gray-700 border border-gray-600 rounded-md pl-8 pr-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:border-blue-500 w-48"
                />
              </div>
              <select value={filterType} onChange={e => setFilterType(e.target.value)}
                className="bg-gray-700 border border-gray-600 rounded-md px-2 py-1.5 text-sm text-gray-300">
                <option value="">All Types</option>
                <option value="firewall">Firewalls</option>
                <option value="switch">Switches</option>
                <option value="router">Routers</option>
                <option value="modem">Modems</option>
              </select>
              <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
                className="bg-gray-700 border border-gray-600 rounded-md px-2 py-1.5 text-sm text-gray-300">
                <option value="">All Status</option>
                <option value="operational">Operational</option>
                <option value="degraded">Degraded</option>
                <option value="offline">Offline</option>
                <option value="maintenance">Maintenance</option>
              </select>
              <button onClick={fetchData} className="p-1.5 text-gray-400 hover:text-white">
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-xs border-b border-gray-700">
                  <th className="text-left py-2 px-2">Device</th>
                  <th className="text-left py-2 px-2">Type</th>
                  <th className="text-left py-2 px-2">Manufacturer</th>
                  <th className="text-left py-2 px-2">Status</th>
                  <th className="text-left py-2 px-2">Compliance</th>
                  <th className="text-right py-2 px-2">CPU</th>
                  <th className="text-right py-2 px-2">Mem</th>
                </tr>
              </thead>
              <tbody>
                {filteredDevices.map(device => (
                  <tr key={device.device_id}
                    onClick={() => handleDeviceClick(device)}
                    className="border-b border-gray-700/50 hover:bg-gray-700/30 cursor-pointer transition-colors"
                  >
                    <td className="py-2 px-2">
                      <div className="text-gray-200">{device.hostname}</div>
                      <div className="text-xs text-gray-500">{device.management_ip || device.device_id}</div>
                    </td>
                    <td className="py-2 px-2">
                      <span className={`text-xs px-2 py-0.5 rounded border ${deviceTypeColors[device.device_type] || 'bg-gray-500/20 text-gray-400'}`}>
                        {device.device_type}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-gray-400">{device.manufacturer}</td>
                    <td className="py-2 px-2">
                      <span className={`flex items-center gap-1.5 text-xs ${
                        device.status === 'operational' ? 'text-green-400' :
                        device.status === 'degraded' ? 'text-yellow-400' :
                        device.status === 'offline' ? 'text-red-400' : 'text-blue-400'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          device.status === 'operational' ? 'bg-green-400' :
                          device.status === 'degraded' ? 'bg-yellow-400' :
                          device.status === 'offline' ? 'bg-red-400' : 'bg-blue-400'
                        }`} />
                        {device.status}
                      </span>
                    </td>
                    <td className="py-2 px-2">
                      <span className={`text-xs ${
                        device.compliance_status === 'compliant' ? 'text-green-400' :
                        device.compliance_status === 'drifted' ? 'text-yellow-400' : 'text-red-400'
                      }`}>
                        {device.compliance_status}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right text-gray-400 text-xs">{device.cpu_utilization?.toFixed(0)}%</td>
                    <td className="py-2 px-2 text-right text-gray-400 text-xs">{device.memory_utilization?.toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredDevices.length === 0 && (
              <p className="text-center text-gray-500 py-8 text-sm">No devices found</p>
            )}
          </div>
        </div>

        {/* Right column: Compliance + Activity */}
        <div className="space-y-6">
          <ComplianceOverview summary={complianceSummary} onScan={handleComplianceScan} scanning={scanning} />
          <AgentActivityFeed changes={recentChanges} />
        </div>
      </div>

      {/* Change Requests - full width */}
      <ChangeRequestPanel
        requests={changeRequests}
        onApprove={handleApprove}
        onReject={handleReject}
        onExecute={handleExecute}
        loading={actionLoading}
      />

      {/* Device Detail Modal */}
      {selectedDevice && (
        <DeviceDetailModal
          device={selectedDevice.device}
          recentChanges={selectedDevice.recent_changes}
          complianceHistory={selectedDevice.compliance_history}
          onClose={() => setSelectedDevice(null)}
          onSync={handleSync}
        />
      )}
    </div>
  );
}

function SummaryCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: number | string }) {
  return (
    <div className="bg-gray-800 rounded-xl p-4 flex items-center gap-3">
      <div className="p-2 bg-gray-700/50 rounded-lg">{icon}</div>
      <div>
        <p className="text-xl font-bold text-white">{value}</p>
        <p className="text-xs text-gray-500">{label}</p>
      </div>
    </div>
  );
}
