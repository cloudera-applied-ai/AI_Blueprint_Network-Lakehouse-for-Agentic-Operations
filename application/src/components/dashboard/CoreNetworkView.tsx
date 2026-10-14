import { memo, useState, useEffect, useMemo } from 'react';
import {
  Server, Network, Building2,
  Globe, RefreshCw, Cpu, Radio, Zap, Shield,
  CheckCircle2, AlertTriangle, XCircle, Wrench, ChevronDown, ChevronUp
} from 'lucide-react';
import { ResponsiveContainer, YAxis, XAxis, Tooltip, BarChart, Bar } from 'recharts';
import { apiClient } from '@/services/apiClient';
import {
  getHubs, getAmplifiers, getNetworkDevices,
  type Hub, type Amplifier, type NetworkDevice,
} from '@/services/api/coreNetworkApi';

// Types for cable ISP core network
interface Headend {
  headend_id: string;
  name: string;
  region: string;
  service_area: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  cmts_count: number;
  total_cmts_ports: number;
  active_cmts_ports: number;
  port_utilization_percent: number;
  video_server_count: number;
  core_router_count: number;
  peering_capacity_gbps: number;
  total_rack_units: number;
  power_capacity_mw: number;
  total_homes_served: number;
  total_active_subscribers: number;
  status: string;
}

interface CMTSDevice {
  cmts_id: string;
  headend_id: string;
  manufacturer: string;
  model: string;
  firmware_version: string;
  total_ds_ports: number;
  total_us_ports: number;
  active_modems: number;
  registered_modems: number;
  offline_modems: number;
  max_modems_capacity: number;
  modem_utilization_percent: number;
  avg_ds_utilization: number;
  avg_us_utilization: number;
  ranging_success_rate: number;
  t3_timeouts_24h: number;
  t4_timeouts_24h: number;
  cpu_utilization: number;
  memory_utilization: number;
  temperature_celsius: number;
  uplink_capacity_gbps: number;
  status: string;
}

interface CoreNetworkSummary {
  total_headends: number;
  total_cmts: number;
  total_nodes: number;
  total_hubs: number;
  total_amplifiers: number;
  total_network_devices: number;
  total_active_customers: number;
  total_homes_served: number;
  total_subscribers: number;
  total_cmts_ports: number;
  total_active_modems: number;
  headend_health: {
    operational: number;
    degraded: number;
    maintenance: number;
    failed: number;
  };
  cmts_health: {
    operational: number;
    degraded: number;
    maintenance: number;
    failed: number;
  };
  by_region: Record<string, {
    headends: number;
    cmts_devices: number;
    total_homes_served: number;
    total_subscribers: number;
  }>;
}

interface CoreNetworkViewProps {
  selectedRegion?: string | null;
}

const StatusBadge = ({ status }: { status: string }) => {
  const colors: Record<string, string> = {
    operational: 'bg-green-900/50 text-green-400',
    degraded: 'bg-yellow-900/50 text-yellow-400',
    maintenance: 'bg-blue-900/50 text-blue-400',
    failed: 'bg-red-900/50 text-red-400',
  };

  const icons: Record<string, React.ReactNode> = {
    operational: <CheckCircle2 className="w-3 h-3" />,
    degraded: <AlertTriangle className="w-3 h-3" />,
    maintenance: <Wrench className="w-3 h-3" />,
    failed: <XCircle className="w-3 h-3" />,
  };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full ${colors[status] || 'bg-gray-700 text-gray-300'}`}>
      {icons[status]}
      {status}
    </span>
  );
};

const UtilizationBar = ({ value, label }: { value: number; label?: string }) => {
  const color = value > 85 ? 'bg-red-500' : value > 70 ? 'bg-yellow-500' : 'bg-green-500';
  return (
    <div className="w-full">
      {label && <div className="flex justify-between text-xs text-gray-400 mb-0.5">
        <span>{label}</span>
        <span>{value}%</span>
      </div>}
      <div className="w-full bg-gray-700 rounded-full h-1.5">
        <div className={`${color} rounded-full h-1.5 transition-all`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  );
};

const CoreNetworkView = memo(({ selectedRegion }: CoreNetworkViewProps) => {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<CoreNetworkSummary | null>(null);
  const [headends, setHeadends] = useState<Headend[]>([]);
  const [equipment, setEquipment] = useState<CMTSDevice[]>([]);
  const [hubs, setHubs] = useState<Hub[]>([]);
  const [amplifiers, setAmplifiers] = useState<Amplifier[]>([]);
  const [networkDevices, setNetworkDevices] = useState<NetworkDevice[]>([]);
  const [filterRegion, setFilterRegion] = useState<string>(selectedRegion || '');
  const [expandedSection, setExpandedSection] = useState<string | null>('headends');
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Get available regions from summary data
  const availableRegions = useMemo(() => {
    if (!summary) return [];
    return Object.keys(summary.by_region).sort();
  }, [summary]);

  // Fetch all core network data
  const fetchData = async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (filterRegion) params.region = filterRegion;

      const queryString = Object.keys(params).length
        ? '?' + new URLSearchParams(params).toString()
        : '';

      const [summaryRes, headendRes, equipmentRes, hubsRes, ampsRes, devicesRes] = await Promise.all([
        apiClient.get<CoreNetworkSummary>(`/core-network/summary${queryString}`),
        apiClient.get<{ total: number; headends: Headend[] }>(`/core-network/headends${queryString}`),
        apiClient.get<{ total: number; equipment: CMTSDevice[] }>(`/core-network/equipment${queryString}`),
        getHubs({ region: filterRegion || undefined }),
        getAmplifiers({ region: filterRegion || undefined, limit: 100 }),
        getNetworkDevices({ region: filterRegion || undefined, limit: 100 }),
      ]);

      setSummary(summaryRes);
      setHeadends(headendRes.headends);
      setEquipment(equipmentRes.equipment);
      setHubs(hubsRes.hubs);
      setAmplifiers(ampsRes.amplifiers);
      setNetworkDevices(devicesRes.devices);
      setLastRefresh(new Date());
    } catch (error) {
      console.error('Failed to fetch core network data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [filterRegion]);

  // Element distribution chart data
  const elementDistribution = useMemo(() => {
    if (!summary) return [];
    return [
      { name: 'Headends', count: summary.total_headends, color: '#8b5cf6' },
      { name: 'Hubs', count: summary.total_hubs, color: '#ec4899' },
      { name: 'CMTS', count: summary.total_cmts, color: '#06b6d4' },
      { name: 'Nodes', count: summary.total_nodes, color: '#10b981' },
      { name: 'Amplifiers', count: summary.total_amplifiers, color: '#f59e0b' },
      { name: 'Net Devices', count: summary.total_network_devices, color: '#ef4444' },
    ];
  }, [summary]);

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  if (loading && !summary) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading Cable Infrastructure Data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Filters */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server className="w-6 h-6 text-purple-400" />
          <h2 className="text-xl font-bold text-white">Cable Infrastructure</h2>
        </div>

        <div className="flex items-center gap-4">
          {/* Region Filter */}
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-gray-400" />
            <select
              value={filterRegion}
              onChange={(e) => setFilterRegion(e.target.value)}
              className="bg-gray-700 text-gray-200 text-sm rounded px-3 py-1.5 border border-gray-600 focus:outline-none focus:border-blue-500"
            >
              <option value="">All Regions</option>
              {availableRegions.map(region => (
                <option key={region} value={region}>{region.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>

          {/* Refresh Button */}
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 text-gray-200 text-sm rounded hover:bg-gray-600 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>

          <span className="text-xs text-gray-500">
            Last: {lastRefresh.toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          {/* Headends & Subscribers */}
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-400">Headends</h3>
              <Building2 className="w-5 h-5 text-purple-400" />
            </div>
            <p className="text-3xl font-bold text-white">{summary.total_headends}</p>
            <div className="mt-2 space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500">Homes Served</span>
                <span className="text-gray-300">{(summary.total_homes_served / 1000).toFixed(0)}K</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Active Subscribers</span>
                <span className="text-cyan-400">{(summary.total_subscribers / 1000).toFixed(0)}K</span>
              </div>
            </div>
          </div>

          {/* CMTS Health */}
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-400">CMTS Devices</h3>
              <Cpu className="w-5 h-5 text-cyan-400" />
            </div>
            <p className="text-3xl font-bold text-white">{summary.total_cmts}</p>
            <div className="mt-2 space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-green-400">Operational</span>
                <span className="text-green-400">{summary.cmts_health.operational}</span>
              </div>
              {summary.cmts_health.degraded > 0 && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-yellow-400">Degraded</span>
                  <span className="text-yellow-400">{summary.cmts_health.degraded}</span>
                </div>
              )}
              {summary.cmts_health.failed > 0 && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-red-400">Failed</span>
                  <span className="text-red-400">{summary.cmts_health.failed}</span>
                </div>
              )}
            </div>
          </div>

          {/* Infrastructure Distribution Chart */}
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-400">Infrastructure</h3>
              <Network className="w-5 h-5 text-green-400" />
            </div>
            <div className="h-24">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={elementDistribution} layout="vertical" margin={{ left: 0, right: 5, top: 0, bottom: 0 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" width={55} tick={{ fontSize: 10, fill: '#5B6170' }} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-gray-900 border border-gray-700 px-2 py-1 rounded text-xs">
                            <span className="text-white">{payload[0].payload.name}: {Number(payload[0].value).toLocaleString()}</span>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Plant Equipment */}
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-400">Plant Equipment</h3>
              <Zap className="w-5 h-5 text-amber-400" />
            </div>
            <p className="text-3xl font-bold text-white">{summary.total_nodes.toLocaleString()}</p>
            <p className="text-xs text-gray-500 mb-2">Fiber Nodes</p>
            <div className="mt-1 space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500">Hubs</span>
                <span className="text-pink-400">{summary.total_hubs.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Amplifiers</span>
                <span className="text-amber-400">{summary.total_amplifiers.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Network Devices</span>
                <span className="text-red-400">{summary.total_network_devices.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Collapsible Sections */}
      <div className="space-y-4">
        {/* Headends Section */}
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <button
            onClick={() => toggleSection('headends')}
            className="w-full p-4 flex items-center justify-between hover:bg-gray-700/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Building2 className="w-5 h-5 text-purple-400" />
              <span className="font-medium text-white">Headends / Central Offices</span>
              <span className="text-sm text-gray-400">({headends.length})</span>
            </div>
            {expandedSection === 'headends' ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
          </button>

          {expandedSection === 'headends' && (
            <div className="px-4 pb-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {headends.slice(0, 12).map(h => (
                  <div key={h.headend_id} className="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h4 className="font-medium text-white">{h.name}</h4>
                        <p className="text-xs text-gray-500">{h.headend_id} &bull; {h.city}, {h.state} &bull; {h.region}</p>
                      </div>
                      <StatusBadge status={h.status} />
                    </div>
                    <div className="grid grid-cols-4 gap-3 text-xs mb-3">
                      <div>
                        <p className="text-gray-500">CMTS</p>
                        <p className="text-gray-200">{h.cmts_count}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Homes Served</p>
                        <p className="text-gray-200">{(h.total_homes_served / 1000).toFixed(0)}K</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Subscribers</p>
                        <p className="text-cyan-400">{(h.total_active_subscribers / 1000).toFixed(0)}K</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Peering</p>
                        <p className="text-gray-200">{h.peering_capacity_gbps} Gbps</p>
                      </div>
                    </div>
                    <UtilizationBar value={h.port_utilization_percent} label="CMTS Port Utilization" />
                    <div className="mt-2 flex flex-wrap gap-1">
                      <span className="px-2 py-0.5 text-xs bg-gray-700 rounded text-gray-300">
                        Routers: {h.core_router_count}
                      </span>
                      <span className="px-2 py-0.5 text-xs bg-gray-700 rounded text-gray-300">
                        Video: {h.video_server_count}
                      </span>
                      <span className="px-2 py-0.5 text-xs bg-gray-700 rounded text-gray-300">
                        Racks: {h.total_rack_units}
                      </span>
                      <span className="px-2 py-0.5 text-xs bg-gray-700 rounded text-gray-300">
                        Power: {h.power_capacity_mw} MW
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              {headends.length > 12 && (
                <p className="text-center text-gray-500 text-sm mt-4">
                  Showing 12 of {headends.length} headends
                </p>
              )}
            </div>
          )}
        </div>

        {/* CMTS Equipment Section */}
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <button
            onClick={() => toggleSection('equipment')}
            className="w-full p-4 flex items-center justify-between hover:bg-gray-700/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Radio className="w-5 h-5 text-cyan-400" />
              <span className="font-medium text-white">CMTS Equipment</span>
              <span className="text-sm text-gray-400">({equipment.length})</span>
            </div>
            {expandedSection === 'equipment' ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
          </button>

          {expandedSection === 'equipment' && (
            <div className="px-4 pb-4">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-400 border-b border-gray-700">
                      <th className="pb-2 font-medium">CMTS ID</th>
                      <th className="pb-2 font-medium">Headend</th>
                      <th className="pb-2 font-medium">Model</th>
                      <th className="pb-2 font-medium">Status</th>
                      <th className="pb-2 font-medium">Modems</th>
                      <th className="pb-2 font-medium">DS Util</th>
                      <th className="pb-2 font-medium">US Util</th>
                      <th className="pb-2 font-medium">CPU</th>
                      <th className="pb-2 font-medium">Ranging</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-300">
                    {equipment.slice(0, 20).map(c => (
                      <tr key={c.cmts_id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                        <td className="py-2 font-mono text-xs">{c.cmts_id}</td>
                        <td className="py-2 text-xs">{c.headend_id}</td>
                        <td className="py-2 text-xs">{c.manufacturer} {c.model}</td>
                        <td className="py-2"><StatusBadge status={c.status} /></td>
                        <td className="py-2">
                          {c.active_modems.toLocaleString()}/{c.max_modems_capacity.toLocaleString()}
                          <span className={`ml-1 ${c.modem_utilization_percent > 85 ? 'text-red-400' : c.modem_utilization_percent > 70 ? 'text-yellow-400' : 'text-gray-500'}`}>
                            ({c.modem_utilization_percent}%)
                          </span>
                        </td>
                        <td className={`py-2 ${c.avg_ds_utilization > 80 ? 'text-red-400' : c.avg_ds_utilization > 60 ? 'text-yellow-400' : ''}`}>
                          {c.avg_ds_utilization}%
                        </td>
                        <td className={`py-2 ${c.avg_us_utilization > 80 ? 'text-red-400' : c.avg_us_utilization > 60 ? 'text-yellow-400' : ''}`}>
                          {c.avg_us_utilization}%
                        </td>
                        <td className={`py-2 ${c.cpu_utilization > 80 ? 'text-red-400' : c.cpu_utilization > 60 ? 'text-yellow-400' : ''}`}>
                          {c.cpu_utilization}%
                        </td>
                        <td className={`py-2 ${c.ranging_success_rate < 95 ? 'text-red-400' : c.ranging_success_rate < 98 ? 'text-yellow-400' : 'text-green-400'}`}>
                          {c.ranging_success_rate}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {equipment.length > 20 && (
                <p className="text-center text-gray-500 text-sm mt-4">
                  Showing 20 of {equipment.length} CMTS devices
                </p>
              )}
            </div>
          )}
        </div>

        {/* Hubs Section */}
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <button
            onClick={() => toggleSection('hubs')}
            className="w-full p-4 flex items-center justify-between hover:bg-gray-700/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Network className="w-5 h-5 text-pink-400" />
              <span className="font-medium text-white">Hubs</span>
              <span className="text-sm text-gray-400">({hubs.length})</span>
            </div>
            {expandedSection === 'hubs' ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
          </button>

          {expandedSection === 'hubs' && (
            <div className="px-4 pb-4">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-400 border-b border-gray-700">
                      <th className="pb-2 font-medium">Hub</th>
                      <th className="pb-2 font-medium">Headend</th>
                      <th className="pb-2 font-medium">Location</th>
                      <th className="pb-2 font-medium">Status</th>
                      <th className="pb-2 font-medium">Nodes</th>
                      <th className="pb-2 font-medium">Homes</th>
                      <th className="pb-2 font-medium">Utilization</th>
                      <th className="pb-2 font-medium">Power</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-300">
                    {hubs.slice(0, 20).map(h => (
                      <tr key={h.hub_id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                        <td className="py-2">
                          <div className="font-mono text-xs">{h.hub_id}</div>
                          <div className="text-xs text-gray-500">{h.name}</div>
                        </td>
                        <td className="py-2 text-xs">{h.headend_id}</td>
                        <td className="py-2 text-xs">{h.city}, {h.state}</td>
                        <td className="py-2"><StatusBadge status={h.status} /></td>
                        <td className="py-2 text-xs">{h.fiber_nodes_served}</td>
                        <td className="py-2 text-xs">{(h.total_homes_served / 1000).toFixed(0)}K</td>
                        <td className="py-2">
                          <UtilizationBar value={h.utilization_percent} label={`${h.current_throughput_gbps}/${h.fiber_capacity_gbps} Gbps`} />
                        </td>
                        <td className={`py-2 text-xs ${h.power_status === 'normal' ? 'text-green-400' : 'text-yellow-400'}`}>
                          {h.power_status}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {hubs.length > 20 && (
                <p className="text-center text-gray-500 text-sm mt-4">
                  Showing 20 of {hubs.length} hubs
                </p>
              )}
            </div>
          )}
        </div>

        {/* Amplifiers Section */}
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <button
            onClick={() => toggleSection('amplifiers')}
            className="w-full p-4 flex items-center justify-between hover:bg-gray-700/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Zap className="w-5 h-5 text-amber-400" />
              <span className="font-medium text-white">Amplifiers</span>
              <span className="text-sm text-gray-400">({amplifiers.length})</span>
            </div>
            {expandedSection === 'amplifiers' ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
          </button>

          {expandedSection === 'amplifiers' && (
            <div className="px-4 pb-4">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-400 border-b border-gray-700">
                      <th className="pb-2 font-medium">Amp ID</th>
                      <th className="pb-2 font-medium">Node</th>
                      <th className="pb-2 font-medium">Type</th>
                      <th className="pb-2 font-medium">Status</th>
                      <th className="pb-2 font-medium">DS SNR</th>
                      <th className="pb-2 font-medium">US SNR</th>
                      <th className="pb-2 font-medium">Temp</th>
                      <th className="pb-2 font-medium">Power</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-300">
                    {amplifiers.slice(0, 20).map(a => (
                      <tr key={a.amp_id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                        <td className="py-2 font-mono text-xs">{a.amp_id}</td>
                        <td className="py-2 text-xs">{a.node_id}</td>
                        <td className="py-2 text-xs capitalize">{a.amp_type?.replace(/_/g, ' ')}</td>
                        <td className="py-2"><StatusBadge status={a.status} /></td>
                        <td className={`py-2 text-xs ${a.ds_snr < 30 ? 'text-red-400' : a.ds_snr < 35 ? 'text-yellow-400' : 'text-green-400'}`}>
                          {a.ds_snr} dB
                        </td>
                        <td className={`py-2 text-xs ${a.us_snr < 20 ? 'text-red-400' : a.us_snr < 25 ? 'text-yellow-400' : 'text-green-400'}`}>
                          {a.us_snr} dB
                        </td>
                        <td className={`py-2 text-xs ${a.temperature_celsius > 60 ? 'text-red-400' : a.temperature_celsius > 45 ? 'text-yellow-400' : ''}`}>
                          {a.temperature_celsius}°C
                        </td>
                        <td className={`py-2 text-xs ${a.power_supply_status === 'normal' ? 'text-green-400' : a.power_supply_status === 'degraded' ? 'text-yellow-400' : 'text-red-400'}`}>
                          {a.power_supply_status}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {amplifiers.length > 20 && (
                <p className="text-center text-gray-500 text-sm mt-4">
                  Showing 20 of {amplifiers.length} amplifiers
                </p>
              )}
            </div>
          )}
        </div>

        {/* Network Devices Section */}
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <button
            onClick={() => toggleSection('network-devices')}
            className="w-full p-4 flex items-center justify-between hover:bg-gray-700/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Shield className="w-5 h-5 text-red-400" />
              <span className="font-medium text-white">Network Devices</span>
              <span className="text-sm text-gray-400">({networkDevices.length})</span>
            </div>
            {expandedSection === 'network-devices' ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
          </button>

          {expandedSection === 'network-devices' && (
            <div className="px-4 pb-4">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-400 border-b border-gray-700">
                      <th className="pb-2 font-medium">Hostname</th>
                      <th className="pb-2 font-medium">Type</th>
                      <th className="pb-2 font-medium">Role</th>
                      <th className="pb-2 font-medium">Status</th>
                      <th className="pb-2 font-medium">Manufacturer</th>
                      <th className="pb-2 font-medium">Compliance</th>
                      <th className="pb-2 font-medium">CPU</th>
                      <th className="pb-2 font-medium">Memory</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-300">
                    {networkDevices.slice(0, 20).map(d => (
                      <tr key={d.device_id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                        <td className="py-2">
                          <div className="text-xs font-medium">{d.hostname}</div>
                          <div className="text-xs text-gray-500">{d.management_ip}</div>
                        </td>
                        <td className="py-2 text-xs capitalize">{d.device_type}</td>
                        <td className="py-2 text-xs capitalize">{d.device_role}</td>
                        <td className="py-2"><StatusBadge status={d.status} /></td>
                        <td className="py-2 text-xs">{d.manufacturer}<br /><span className="text-gray-500">{d.hardware_model}</span></td>
                        <td className="py-2">
                          <span className={`text-xs ${d.compliance_status === 'compliant' ? 'text-green-400' : d.compliance_status === 'drifted' ? 'text-yellow-400' : 'text-red-400'}`}>
                            {d.compliance_status}
                          </span>
                        </td>
                        <td className={`py-2 text-xs ${d.cpu_utilization > 80 ? 'text-red-400' : d.cpu_utilization > 60 ? 'text-yellow-400' : ''}`}>
                          {d.cpu_utilization}%
                        </td>
                        <td className={`py-2 text-xs ${d.memory_utilization > 80 ? 'text-red-400' : d.memory_utilization > 60 ? 'text-yellow-400' : ''}`}>
                          {d.memory_utilization}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {networkDevices.length > 20 && (
                <p className="text-center text-gray-500 text-sm mt-4">
                  Showing 20 of {networkDevices.length} network devices
                </p>
              )}
            </div>
          )}
        </div>

        {/* Regional Breakdown */}
        {summary && Object.keys(summary.by_region).length > 1 && (
          <div className="bg-gray-800 rounded-lg border border-gray-700">
            <button
              onClick={() => toggleSection('regions')}
              className="w-full p-4 flex items-center justify-between hover:bg-gray-700/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <Globe className="w-5 h-5 text-green-400" />
                <span className="font-medium text-white">Regional Breakdown</span>
                <span className="text-sm text-gray-400">({Object.keys(summary.by_region).length} regions)</span>
              </div>
              {expandedSection === 'regions' ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
            </button>

            {expandedSection === 'regions' && (
              <div className="px-4 pb-4">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-400 border-b border-gray-700">
                        <th className="pb-2 font-medium">Region</th>
                        <th className="pb-2 font-medium">Headends</th>
                        <th className="pb-2 font-medium">CMTS</th>
                        <th className="pb-2 font-medium">Homes Served</th>
                        <th className="pb-2 font-medium">Subscribers</th>
                      </tr>
                    </thead>
                    <tbody className="text-gray-300">
                      {Object.entries(summary.by_region)
                        .sort(([, a], [, b]) => b.total_subscribers - a.total_subscribers)
                        .map(([region, data]) => (
                          <tr key={region} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                            <td className="py-2 font-medium">{region.replace(/_/g, ' ')}</td>
                            <td className="py-2">{data.headends}</td>
                            <td className="py-2">{data.cmts_devices}</td>
                            <td className="py-2">{(data.total_homes_served / 1000).toFixed(0)}K</td>
                            <td className="py-2 text-cyan-400">{(data.total_subscribers / 1000).toFixed(0)}K</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
});

CoreNetworkView.displayName = 'CoreNetworkView';

export default CoreNetworkView;
