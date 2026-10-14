import { memo, useState, useEffect } from 'react';
import { FiberNode, Alert, SelfHealingAction } from '@/types';
import { X, Activity, Radio, Calendar, AlertTriangle, Wrench, Clock, CheckCircle2, XCircle, Server, Building2, Zap, Signal, Network, Settings, FileText, Users, Wifi, MapPin, Shield, TrendingUp, Cpu, Fan, Power, HardDrive, ChevronDown, ChevronUp, Battery } from 'lucide-react';
import { formatTimestamp, formatNumber, getStatusColor, calculateActionProgress, formatDuration } from '@/utils/helpers';
import { apiClient } from '@/services/apiClient';
import { LineChart, Line, ResponsiveContainer, YAxis, XAxis, Tooltip } from 'recharts';

// Equipment data interfaces
interface AAUUnit {
  aau_id: string;
  sector_id: string;
  manufacturer: string;
  model: string;
  status: string;
  frequency_bands: string;
  current_tx_power_watts: number;
  max_tx_power_watts: number;
  temperature_celsius: number;
  power_consumption_watts: number;
  vswr: number;
  efficiency_percent: number;
  mimo_config: string;
  beamforming_enabled: boolean;
  last_maintenance: string;
}

interface BBUUnit {
  bbu_id: string;
  manufacturer: string;
  model: string;
  status: string;
  cpu_utilization_percent: number;
  memory_utilization_percent: number;
  temperature_celsius: number;
  active_connections: number;
  max_connections: number;
  current_throughput_gbps: number;
  uptime_hours: number;
  fronthaul_status: string;
  backhaul_status: string;
}

interface HVACUnit {
  hvac_id: string;
  manufacturer: string;
  model: string;
  status: string;
  current_mode: string;
  setpoint_celsius: number;
  current_temp_celsius: number;
  humidity_percent: number;
  power_consumption_watts: number;
  compressor_status: string;
  filter_condition: string;
  high_temp_alarm: boolean;
  compressor_fault: boolean;
  last_maintenance: string;
}

interface PowerSystem {
  power_id: string;
  primary_source: string;
  backup_type: string;
  battery_backup_hours: number;
  battery_health_percent: number;
  battery_temperature_celsius: number;
  current_load_kw: number;
  max_load_kw: number;
  grid_status: string;
  grid_voltage: number;
  generator_status: string;
  generator_fuel_level_percent: number | null;
  ups_status: string;
  power_efficiency_percent: number;
  total_outages_ytd: number;
}

interface EquipmentData {
  node_id: string;
  aau_units: AAUUnit[];
  bbu: BBUUnit;
  hvac: HVACUnit;
  power: PowerSystem;
  summary: {
    overall_health: string;
    aau_status: string;
    bbu_status: string;
    hvac_status: string;
    power_status: string;
  };
}

// Equipment history data interfaces
interface EquipmentHistoryPoint {
  timestamp: string;
  aau: {
    avg_temperature_celsius: number;
    avg_efficiency_percent: number;
    units_operational: number;
    total_units: number;
  };
  bbu: {
    cpu_utilization_percent: number;
    memory_utilization_percent: number;
    temperature_celsius: number;
    throughput_gbps: number;
  };
  hvac: {
    current_temp_celsius: number;
    setpoint_celsius: number;
    humidity_percent: number;
    power_consumption_watts: number;
    compressor_running: boolean;
  };
  power: {
    current_load_kw: number;
    max_load_kw: number;
    load_percent: number;
    grid_voltage: number;
    battery_health_percent: number;
    ups_on_battery: boolean;
  };
}

interface EquipmentHistoryResponse {
  node_id: string;
  period_days: number;
  data_points: number;
  history: EquipmentHistoryPoint[];
  statistics: {
    aau: {
      temperature: { min: number; max: number; avg: number; current: number; trend: string };
      efficiency: { min: number; max: number; avg: number; current: number; trend: string };
    };
    bbu: {
      cpu_utilization: { min: number; max: number; avg: number; current: number; trend: string };
      memory_utilization: { min: number; max: number; avg: number; current: number; trend: string };
      temperature: { min: number; max: number; avg: number; current: number; trend: string };
    };
    hvac: {
      temperature: { min: number; max: number; avg: number; current: number; trend: string };
    };
    power: {
      load: { min: number; max: number; avg: number; current: number; trend: string };
      battery_health: { min: number; max: number; avg: number; current: number; trend: string };
    };
  };
}

interface NodeDetailModalProps {
  node: FiberNode;
  alerts: Alert[];
  actions: SelfHealingAction[];
  onClose: () => void;
}

const NodeDetailModal = memo(({ node, alerts, actions, onClose }: NodeDetailModalProps) => {
  const [_currentTime, setCurrentTime] = useState(Date.now());
  const [showAllActions, setShowAllActions] = useState(false);
  const [equipmentData, setEquipmentData] = useState<EquipmentData | null>(null);
  const [equipmentHistory, setEquipmentHistory] = useState<EquipmentHistoryResponse | null>(null);
  const [equipmentLoading, setEquipmentLoading] = useState(true);
  const [showEquipmentDetails, setShowEquipmentDetails] = useState(false);

  // Fetch equipment data and history for this node
  useEffect(() => {
    const fetchEquipment = async () => {
      try {
        setEquipmentLoading(true);
        const [data, history] = await Promise.all([
          apiClient.get<EquipmentData>(`/nodes/${node.node_id}/equipment`),
          apiClient.get<EquipmentHistoryResponse>(`/nodes/${node.node_id}/equipment/history?days=7`)
        ]);
        setEquipmentData(data);
        setEquipmentHistory(history);
      } catch (error) {
        console.error('Failed to fetch equipment data:', error);
      } finally {
        setEquipmentLoading(false);
      }
    };

    fetchEquipment();
  }, [node.node_id]);

  // Auto-refresh progress every second
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Keyboard shortcut: ESC to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Get active and resolved issues
  const activeAlerts = alerts.filter(alert => alert.status === 'active');
  const resolvedAlerts = alerts.filter(alert => alert.status === 'resolved');

  // Get actions categorized by status
  const activeActions = actions.filter(a => a.status === 'pending' || a.status === 'in_progress');
  const completedActions = actions.filter(a => a.status === 'completed');
  const failedActions = actions.filter(a => a.status === 'failed');

  // Get most recent action
  const recentAction = actions.length > 0 ? actions[0] : null;

  // Calculate overall progress (recalculates with currentTime)
  const overallProgress = recentAction ? calculateActionProgress(recentAction) : 0;

  // Calculate statistics
  const totalActions = actions.length;
  const successRate = totalActions > 0 ? (completedActions.length / totalActions) * 100 : 0;
  const avgResolutionTime = completedActions.length > 0
    ? completedActions.reduce((sum, action) => {
        const duration = action.completion_time
          ? (action.completion_time.getTime() - action.timestamp.getTime()) / 1000
          : 0;
        return sum + duration;
      }, 0) / completedActions.length
    : 0;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4"
      style={{ zIndex: 9999 }}
      onClick={handleBackdropClick}
    >
      <div className="bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-gray-700" style={{ position: 'relative', zIndex: 10000 }}>
        {/* Header */}
        <div className="sticky top-0 bg-gray-800 border-b border-gray-700 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">{node.node_id}</h2>
            <p className="text-sm text-gray-400">
              {node.city ? `${node.city}, ` : ''}{node.region}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-300 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Executive Summary - Always shown for ALL nodes */}
          <div className="bg-gradient-to-r from-gray-800 to-gray-700 rounded-lg p-5 border border-gray-600">
            <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-400" />
              Executive Summary
            </h3>

            {/* Key Status Indicators */}
            <div className="grid grid-cols-4 gap-4 mb-4">
              <div className="text-center">
                <div className={`w-12 h-12 mx-auto rounded-full flex items-center justify-center mb-2 ${
                  node.status === 'healthy' ? 'bg-green-600' :
                  node.status === 'degraded' ? 'bg-yellow-600' :
                  node.status === 'outage' ? 'bg-red-600' :
                  'bg-gray-600'
                }`}>
                  <Activity className="w-6 h-6 text-white" />
                </div>
                <p className="text-xs text-gray-400">Status</p>
                <p className={`text-sm font-bold ${
                  node.status === 'healthy' ? 'text-green-400' :
                  node.status === 'degraded' ? 'text-yellow-400' :
                  node.status === 'outage' ? 'text-red-400' :
                  'text-gray-400'
                }`}>{node.status.toUpperCase()}</p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 mx-auto rounded-full bg-blue-600 flex items-center justify-center mb-2">
                  <Users className="w-6 h-6 text-white" />
                </div>
                <p className="text-xs text-gray-400">Homes Active</p>
                <p className="text-sm font-bold text-white">{formatNumber(node.homes_active || 0)}</p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 mx-auto rounded-full bg-purple-600 flex items-center justify-center mb-2">
                  <Wifi className="w-6 h-6 text-white" />
                </div>
                <p className="text-xs text-gray-400">DOCSIS Version</p>
                <p className="text-sm font-bold text-white">{node.docsis_version || 'N/A'}</p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 mx-auto rounded-full bg-cyan-600 flex items-center justify-center mb-2">
                  <Radio className="w-6 h-6 text-white" />
                </div>
                <p className="text-xs text-gray-400">Coax Plant</p>
                <p className="text-sm font-bold text-white">{node.coax_plant_miles ? `${node.coax_plant_miles.toFixed(1)} mi` : 'N/A'}</p>
              </div>
            </div>

            {/* Quick Stats Row */}
            <div className="grid grid-cols-3 gap-3 mb-4 pt-4 border-t border-gray-600">
              <div className="bg-gray-800 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <MapPin className="w-4 h-4 text-green-400" />
                  <span className="text-xs text-gray-400">Location</span>
                </div>
                <p className="text-sm font-medium text-white">{node.city}{node.state ? `, ${node.state}` : ''}</p>
                <p className="text-xs text-gray-500">{node.region}</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Server className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs text-gray-400">Equipment</span>
                </div>
                {equipmentLoading ? (
                  <p className="text-xs text-gray-500">Loading...</p>
                ) : equipmentData ? (
                  <>
                    <p className={`text-sm font-medium ${
                      equipmentData.summary.overall_health === 'healthy' ? 'text-green-400' : 'text-yellow-400'
                    }`}>{equipmentData.summary.overall_health.toUpperCase()}</p>
                    <p className="text-xs text-gray-500">{equipmentData.aau_units.length} AAU, BBU, HVAC, PWR</p>
                  </>
                ) : (
                  <>
                    <p className="text-sm font-medium text-white">{node.manufacturer}</p>
                    <p className="text-xs text-gray-500">{node.hardware_model}</p>
                  </>
                )}
              </div>
              <div className="bg-gray-800 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Shield className="w-4 h-4 text-yellow-400" />
                  <span className="text-xs text-gray-400">Priority / Node Type</span>
                </div>
                <p className="text-sm font-medium text-white">{(node.homes_active || 0) > 500 ? 'Critical' : (node.homes_active || 0) > 200 ? 'Standard' : 'Basic'}</p>
                <p className="text-xs text-gray-500">{node.node_type || 'N+0'}</p>
              </div>
            </div>

            {/* Infrastructure Summary */}
            <div className="grid grid-cols-5 gap-2 text-center pt-3 border-t border-gray-600">
              <div>
                <p className="text-lg font-bold text-white">{node.homes_passed || 'N/A'}</p>
                <p className="text-xs text-gray-400">Homes Passed</p>
              </div>
              <div>
                <p className="text-lg font-bold text-white">{node.amplifier_cascade ?? 'N/A'}</p>
                <p className="text-xs text-gray-400">Amp Cascade</p>
              </div>
              <div>
                <p className="text-lg font-bold text-white">{node.downstream_channels || 'N/A'}</p>
                <p className="text-xs text-gray-400">DS Channels</p>
              </div>
              <div>
                <p className="text-lg font-bold text-white">{node.power_supply_status || 'N/A'}</p>
                <p className="text-xs text-gray-400">Power</p>
              </div>
              <div>
                <p className="text-lg font-bold text-white">{(node.neighbor_nodes || []).length}</p>
                <p className="text-xs text-gray-400">Neighbors</p>
              </div>
            </div>

            {/* Alert/Action Summary - Always shown */}
            <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-gray-600">
              <div className={`rounded-lg p-3 ${activeAlerts.length > 0 ? 'bg-red-900/30 border border-red-600/50' : 'bg-green-900/30 border border-green-600/50'}`}>
                <div className="flex items-center gap-2">
                  <AlertTriangle className={`w-4 h-4 ${activeAlerts.length > 0 ? 'text-red-400' : 'text-green-400'}`} />
                  <span className="text-xs text-gray-400">Active Alerts</span>
                </div>
                <p className={`text-2xl font-bold ${activeAlerts.length > 0 ? 'text-red-400' : 'text-green-400'}`}>{activeAlerts.length}</p>
              </div>
              <div className={`rounded-lg p-3 ${activeActions.length > 0 ? 'bg-blue-900/30 border border-blue-600/50' : 'bg-gray-800 border border-gray-600'}`}>
                <div className="flex items-center gap-2">
                  <Wrench className={`w-4 h-4 ${activeActions.length > 0 ? 'text-blue-400' : 'text-gray-400'}`} />
                  <span className="text-xs text-gray-400">Active Actions</span>
                </div>
                <p className={`text-2xl font-bold ${activeActions.length > 0 ? 'text-blue-400' : 'text-gray-400'}`}>{activeActions.length}</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-3 border border-gray-600">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-purple-400" />
                  <span className="text-xs text-gray-400">Success Rate</span>
                </div>
                <p className="text-2xl font-bold text-purple-400">{totalActions > 0 ? `${successRate.toFixed(0)}%` : 'N/A'}</p>
              </div>
            </div>

            {/* Equipment Status with Line Graphs */}
            {!equipmentLoading && equipmentData && equipmentHistory && (
              <div className="mt-4 pt-4 border-t border-gray-600">
                <div className="flex items-center gap-2 mb-3">
                  <HardDrive className="w-4 h-4 text-cyan-400" />
                  <h4 className="text-xs font-semibold text-gray-300">Equipment Status (7-Day Trends)</h4>
                  <span className={`ml-auto px-2 py-0.5 text-xs rounded-full ${
                    equipmentData.summary.overall_health === 'healthy'
                      ? 'bg-green-900/50 text-green-400'
                      : 'bg-yellow-900/50 text-yellow-400'
                  }`}>
                    {equipmentData.summary.overall_health.toUpperCase()}
                  </span>
                </div>

                {/* Row 1: AAU and BBU */}
                <div className="grid grid-cols-2 gap-3 mb-3">
                  {/* AAU Temperature Graph */}
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5">
                        <Radio className="w-3.5 h-3.5 text-cyan-400" />
                        <span className="text-xs font-medium text-gray-300">AAU Temp</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                          equipmentData.summary.aau_status === 'healthy' ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'
                        }`}>{equipmentData.summary.aau_status}</span>
                      </div>
                      <span className="text-xs font-bold text-cyan-400">
                        {equipmentHistory.statistics.aau.temperature.current}°C
                      </span>
                    </div>
                    <div className="h-14">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={equipmentHistory.history.slice().reverse().map((h, i) => ({ idx: i, value: h.aau.avg_temperature_celsius }))}>
                          <YAxis domain={['dataMin - 5', 'dataMax + 5']} hide />
                          <XAxis dataKey="idx" hide />
                          <Tooltip
                            content={({ active, payload }) => {
                              if (active && payload && payload.length) {
                                return (
                                  <div className="bg-gray-900 border border-gray-700 px-2 py-1 rounded text-xs">
                                    <span className="text-cyan-400">{payload[0].value}°C</span>
                                  </div>
                                );
                              }
                              return null;
                            }}
                          />
                          <Line type="monotone" dataKey="value" stroke="#22d3ee" strokeWidth={2} dot={false} isAnimationActive={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                      <span>Min: {equipmentHistory.statistics.aau.temperature.min}°C</span>
                      <span>Avg: {equipmentHistory.statistics.aau.temperature.avg}°C</span>
                      <span>Max: {equipmentHistory.statistics.aau.temperature.max}°C</span>
                    </div>
                  </div>

                  {/* BBU CPU Graph */}
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5">
                        <Cpu className="w-3.5 h-3.5 text-purple-400" />
                        <span className="text-xs font-medium text-gray-300">BBU CPU</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                          equipmentData.summary.bbu_status === 'operational' ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'
                        }`}>{equipmentData.summary.bbu_status}</span>
                      </div>
                      <span className={`text-xs font-bold ${
                        equipmentHistory.statistics.bbu.cpu_utilization.current > 80 ? 'text-red-400' :
                        equipmentHistory.statistics.bbu.cpu_utilization.current > 60 ? 'text-yellow-400' : 'text-purple-400'
                      }`}>
                        {equipmentHistory.statistics.bbu.cpu_utilization.current}%
                      </span>
                    </div>
                    <div className="h-14">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={equipmentHistory.history.slice().reverse().map((h, i) => ({ idx: i, value: h.bbu.cpu_utilization_percent }))}>
                          <YAxis domain={[0, 100]} hide />
                          <XAxis dataKey="idx" hide />
                          <Tooltip
                            content={({ active, payload }) => {
                              if (active && payload && payload.length) {
                                return (
                                  <div className="bg-gray-900 border border-gray-700 px-2 py-1 rounded text-xs">
                                    <span className="text-purple-400">{payload[0].value}%</span>
                                  </div>
                                );
                              }
                              return null;
                            }}
                          />
                          <Line type="monotone" dataKey="value" stroke="#a855f7" strokeWidth={2} dot={false} isAnimationActive={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                      <span>Min: {equipmentHistory.statistics.bbu.cpu_utilization.min}%</span>
                      <span>Avg: {equipmentHistory.statistics.bbu.cpu_utilization.avg}%</span>
                      <span>Max: {equipmentHistory.statistics.bbu.cpu_utilization.max}%</span>
                    </div>
                  </div>
                </div>

                {/* Row 2: HVAC and Power */}
                <div className="grid grid-cols-2 gap-3 mb-3">
                  {/* HVAC Temperature Graph */}
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5">
                        <Fan className="w-3.5 h-3.5 text-blue-400" />
                        <span className="text-xs font-medium text-gray-300">HVAC Temp</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                          equipmentData.summary.hvac_status === 'operational' ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'
                        }`}>{equipmentData.summary.hvac_status}</span>
                      </div>
                      <span className={`text-xs font-bold ${
                        equipmentHistory.statistics.hvac.temperature.current > 28 ? 'text-yellow-400' : 'text-blue-400'
                      }`}>
                        {equipmentHistory.statistics.hvac.temperature.current}°C
                      </span>
                    </div>
                    <div className="h-14">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={equipmentHistory.history.slice().reverse().map((h, i) => ({ idx: i, value: h.hvac.current_temp_celsius }))}>
                          <YAxis domain={['dataMin - 2', 'dataMax + 2']} hide />
                          <XAxis dataKey="idx" hide />
                          <Tooltip
                            content={({ active, payload }) => {
                              if (active && payload && payload.length) {
                                return (
                                  <div className="bg-gray-900 border border-gray-700 px-2 py-1 rounded text-xs">
                                    <span className="text-blue-400">{payload[0].value}°C</span>
                                  </div>
                                );
                              }
                              return null;
                            }}
                          />
                          <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} isAnimationActive={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                      <span>Min: {equipmentHistory.statistics.hvac.temperature.min}°C</span>
                      <span>Avg: {equipmentHistory.statistics.hvac.temperature.avg}°C</span>
                      <span>Max: {equipmentHistory.statistics.hvac.temperature.max}°C</span>
                    </div>
                  </div>

                  {/* Power Load Graph */}
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5">
                        <Zap className="w-3.5 h-3.5 text-yellow-400" />
                        <span className="text-xs font-medium text-gray-300">Power Load</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                          equipmentData.summary.power_status === 'connected' ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'
                        }`}>{equipmentData.summary.power_status}</span>
                      </div>
                      <span className="text-xs font-bold text-yellow-400">
                        {equipmentHistory.statistics.power.load.current} kW
                      </span>
                    </div>
                    <div className="h-14">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={equipmentHistory.history.slice().reverse().map((h, i) => ({ idx: i, value: h.power.current_load_kw }))}>
                          <YAxis domain={['dataMin - 0.5', 'dataMax + 0.5']} hide />
                          <XAxis dataKey="idx" hide />
                          <Tooltip
                            content={({ active, payload }) => {
                              if (active && payload && payload.length) {
                                return (
                                  <div className="bg-gray-900 border border-gray-700 px-2 py-1 rounded text-xs">
                                    <span className="text-yellow-400">{payload[0].value} kW</span>
                                  </div>
                                );
                              }
                              return null;
                            }}
                          />
                          <Line type="monotone" dataKey="value" stroke="#eab308" strokeWidth={2} dot={false} isAnimationActive={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                      <span>Min: {equipmentHistory.statistics.power.load.min} kW</span>
                      <span>Avg: {equipmentHistory.statistics.power.load.avg} kW</span>
                      <span>Max: {equipmentHistory.statistics.power.load.max} kW</span>
                    </div>
                  </div>
                </div>

                {/* Row 3: UPS/Battery */}
                <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5">
                      <Battery className="w-3.5 h-3.5 text-green-400" />
                      <span className="text-xs font-medium text-gray-300">UPS Battery Health</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                        equipmentData.power.ups_status === 'online' ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'
                      }`}>{equipmentData.power.ups_status}</span>
                    </div>
                    <span className={`text-xs font-bold ${
                      equipmentHistory.statistics.power.battery_health.current < 80 ? 'text-yellow-400' : 'text-green-400'
                    }`}>
                      {equipmentHistory.statistics.power.battery_health.current}%
                    </span>
                  </div>
                  <div className="h-12">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={equipmentHistory.history.slice().reverse().map((h, i) => ({ idx: i, value: h.power.battery_health_percent }))}>
                        <YAxis domain={[70, 100]} hide />
                        <XAxis dataKey="idx" hide />
                        <Tooltip
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              return (
                                <div className="bg-gray-900 border border-gray-700 px-2 py-1 rounded text-xs">
                                  <span className="text-green-400">{payload[0].value}%</span>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                        <Line type="monotone" dataKey="value" stroke="#22c55e" strokeWidth={2} dot={false} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                    <span>Min: {equipmentHistory.statistics.power.battery_health.min}%</span>
                    <span>Avg: {equipmentHistory.statistics.power.battery_health.avg}%</span>
                    <span>Max: {equipmentHistory.statistics.power.battery_health.max}%</span>
                    <span className="text-gray-400">Backup: {equipmentData.power.battery_backup_hours.toFixed(0)}h</span>
                  </div>
                </div>
              </div>
            )}

            {/* Loading state for equipment */}
            {equipmentLoading && (
              <div className="mt-4 pt-4 border-t border-gray-600">
                <div className="flex items-center gap-2 mb-3">
                  <HardDrive className="w-4 h-4 text-cyan-400" />
                  <h4 className="text-xs font-semibold text-gray-300">Equipment Status</h4>
                </div>
                <div className="text-center py-4">
                  <p className="text-xs text-gray-500">Loading equipment data...</p>
                </div>
              </div>
            )}
          </div>

          {/* Equipment Monitoring Section - Detailed View */}
          <div className="bg-gradient-to-r from-gray-800 to-gray-700 rounded-lg border border-gray-600">
            {/* Header - Collapsible */}
            <button
              onClick={() => setShowEquipmentDetails(!showEquipmentDetails)}
              className="w-full p-4 flex items-center justify-between hover:bg-gray-700/50 transition-colors rounded-lg"
            >
              <div className="flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-semibold text-gray-300">Equipment Details</h3>
                {equipmentData && (
                  <span className="text-xs text-gray-400">
                    ({equipmentData.aau_units.length} AAUs, BBU, HVAC, Power)
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Click to {showEquipmentDetails ? 'collapse' : 'expand'}</span>
                {showEquipmentDetails ? (
                  <ChevronUp className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                )}
              </div>
            </button>

            {/* Expanded Equipment Details */}
            {showEquipmentDetails && equipmentData && (
              <div className="px-4 pb-4 space-y-4 border-t border-gray-600 pt-4">
                {/* AAU Units */}
                <div>
                  <h4 className="text-xs font-semibold text-cyan-400 mb-2 flex items-center gap-2">
                    <Radio className="w-3 h-3" />
                    Active Antenna Units ({equipmentData.aau_units.length})
                  </h4>
                  <div className="grid grid-cols-1 gap-2">
                    {equipmentData.aau_units.map((aau) => (
                      <div key={aau.aau_id} className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-white">{aau.aau_id}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            aau.status === 'operational' ? 'bg-green-900/50 text-green-400' :
                            aau.status === 'degraded' ? 'bg-yellow-900/50 text-yellow-400' :
                            'bg-red-900/50 text-red-400'
                          }`}>{aau.status}</span>
                        </div>
                        <div className="grid grid-cols-4 gap-2 text-xs">
                          <div>
                            <p className="text-gray-500">Manufacturer</p>
                            <p className="text-gray-300">{aau.manufacturer}</p>
                          </div>
                          <div>
                            <p className="text-gray-500">Model</p>
                            <p className="text-gray-300">{aau.model}</p>
                          </div>
                          <div>
                            <p className="text-gray-500">TX Power</p>
                            <p className="text-gray-300">{aau.current_tx_power_watts.toFixed(0)}W / {aau.max_tx_power_watts.toFixed(0)}W</p>
                          </div>
                          <div>
                            <p className="text-gray-500">Temperature</p>
                            <p className={aau.temperature_celsius > 50 ? 'text-yellow-400' : 'text-gray-300'}>
                              {aau.temperature_celsius.toFixed(0)}°C
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500">VSWR</p>
                            <p className={aau.vswr > 1.5 ? 'text-yellow-400' : 'text-gray-300'}>
                              {aau.vswr.toFixed(2)}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500">Efficiency</p>
                            <p className="text-gray-300">{aau.efficiency_percent.toFixed(0)}%</p>
                          </div>
                          <div>
                            <p className="text-gray-500">MIMO</p>
                            <p className="text-gray-300">{aau.mimo_config}</p>
                          </div>
                          <div>
                            <p className="text-gray-500">Beamforming</p>
                            <p className={aau.beamforming_enabled ? 'text-green-400' : 'text-gray-500'}>
                              {aau.beamforming_enabled ? 'Enabled' : 'Disabled'}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* BBU */}
                <div>
                  <h4 className="text-xs font-semibold text-purple-400 mb-2 flex items-center gap-2">
                    <Cpu className="w-3 h-3" />
                    Baseband Unit
                  </h4>
                  <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-white">{equipmentData.bbu.bbu_id}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        equipmentData.bbu.status === 'operational' ? 'bg-green-900/50 text-green-400' :
                        equipmentData.bbu.status === 'degraded' ? 'bg-yellow-900/50 text-yellow-400' :
                        'bg-red-900/50 text-red-400'
                      }`}>{equipmentData.bbu.status}</span>
                    </div>
                    <div className="grid grid-cols-4 gap-2 text-xs">
                      <div>
                        <p className="text-gray-500">CPU Usage</p>
                        <div className="flex items-center gap-1">
                          <div className="flex-1 h-1.5 bg-gray-700 rounded-full">
                            <div className={`h-1.5 rounded-full ${
                              equipmentData.bbu.cpu_utilization_percent > 80 ? 'bg-red-500' :
                              equipmentData.bbu.cpu_utilization_percent > 60 ? 'bg-yellow-500' : 'bg-green-500'
                            }`} style={{ width: `${equipmentData.bbu.cpu_utilization_percent}%` }} />
                          </div>
                          <span className="text-gray-300">{equipmentData.bbu.cpu_utilization_percent.toFixed(0)}%</span>
                        </div>
                      </div>
                      <div>
                        <p className="text-gray-500">Memory</p>
                        <div className="flex items-center gap-1">
                          <div className="flex-1 h-1.5 bg-gray-700 rounded-full">
                            <div className={`h-1.5 rounded-full ${
                              equipmentData.bbu.memory_utilization_percent > 80 ? 'bg-red-500' :
                              equipmentData.bbu.memory_utilization_percent > 60 ? 'bg-yellow-500' : 'bg-green-500'
                            }`} style={{ width: `${equipmentData.bbu.memory_utilization_percent}%` }} />
                          </div>
                          <span className="text-gray-300">{equipmentData.bbu.memory_utilization_percent.toFixed(0)}%</span>
                        </div>
                      </div>
                      <div>
                        <p className="text-gray-500">Connections</p>
                        <p className="text-gray-300">{equipmentData.bbu.active_connections} / {equipmentData.bbu.max_connections}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Throughput</p>
                        <p className="text-gray-300">{equipmentData.bbu.current_throughput_gbps.toFixed(1)} Gbps</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Uptime</p>
                        <p className="text-gray-300">{(equipmentData.bbu.uptime_hours / 24).toFixed(0)} days</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Temperature</p>
                        <p className={equipmentData.bbu.temperature_celsius > 50 ? 'text-yellow-400' : 'text-gray-300'}>
                          {equipmentData.bbu.temperature_celsius.toFixed(0)}°C
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Fronthaul</p>
                        <p className={equipmentData.bbu.fronthaul_status === 'connected' ? 'text-green-400' : 'text-yellow-400'}>
                          {equipmentData.bbu.fronthaul_status}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Backhaul</p>
                        <p className={equipmentData.bbu.backhaul_status === 'connected' ? 'text-green-400' : 'text-yellow-400'}>
                          {equipmentData.bbu.backhaul_status}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* HVAC */}
                <div>
                  <h4 className="text-xs font-semibold text-blue-400 mb-2 flex items-center gap-2">
                    <Fan className="w-3 h-3" />
                    HVAC System
                  </h4>
                  <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-white">{equipmentData.hvac.hvac_id}</span>
                      <div className="flex items-center gap-2">
                        {equipmentData.hvac.high_temp_alarm && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-red-900/50 text-red-400">HIGH TEMP</span>
                        )}
                        {equipmentData.hvac.compressor_fault && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-red-900/50 text-red-400">FAULT</span>
                        )}
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          equipmentData.hvac.status === 'operational' ? 'bg-green-900/50 text-green-400' :
                          equipmentData.hvac.status === 'degraded' ? 'bg-yellow-900/50 text-yellow-400' :
                          'bg-red-900/50 text-red-400'
                        }`}>{equipmentData.hvac.status}</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-4 gap-2 text-xs">
                      <div>
                        <p className="text-gray-500">Temperature</p>
                        <p className={equipmentData.hvac.current_temp_celsius > equipmentData.hvac.setpoint_celsius + 5 ? 'text-yellow-400' : 'text-gray-300'}>
                          {equipmentData.hvac.current_temp_celsius.toFixed(1)}°C / {equipmentData.hvac.setpoint_celsius.toFixed(0)}°C
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Humidity</p>
                        <p className="text-gray-300">{equipmentData.hvac.humidity_percent.toFixed(0)}%</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Mode</p>
                        <p className="text-gray-300 capitalize">{equipmentData.hvac.current_mode}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Compressor</p>
                        <p className={equipmentData.hvac.compressor_status === 'running' ? 'text-green-400' :
                          equipmentData.hvac.compressor_status === 'fault' ? 'text-red-400' : 'text-gray-300'}>
                          {equipmentData.hvac.compressor_status}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Power</p>
                        <p className="text-gray-300">{equipmentData.hvac.power_consumption_watts.toFixed(0)}W</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Filter</p>
                        <p className={equipmentData.hvac.filter_condition === 'good' ? 'text-green-400' :
                          equipmentData.hvac.filter_condition === 'replace_soon' ? 'text-yellow-400' : 'text-red-400'}>
                          {equipmentData.hvac.filter_condition.replace('_', ' ')}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Manufacturer</p>
                        <p className="text-gray-300">{equipmentData.hvac.manufacturer}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Model</p>
                        <p className="text-gray-300">{equipmentData.hvac.model}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Power System */}
                <div>
                  <h4 className="text-xs font-semibold text-yellow-400 mb-2 flex items-center gap-2">
                    <Power className="w-3 h-3" />
                    Power System
                  </h4>
                  <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-white">{equipmentData.power.power_id}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        equipmentData.power.grid_status === 'connected' ? 'bg-green-900/50 text-green-400' :
                        'bg-yellow-900/50 text-yellow-400'
                      }`}>Grid: {equipmentData.power.grid_status}</span>
                    </div>
                    <div className="grid grid-cols-4 gap-2 text-xs">
                      <div>
                        <p className="text-gray-500">Primary Source</p>
                        <p className="text-gray-300">{equipmentData.power.primary_source}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Backup</p>
                        <p className="text-gray-300">{equipmentData.power.backup_type}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Load</p>
                        <div className="flex items-center gap-1">
                          <div className="flex-1 h-1.5 bg-gray-700 rounded-full">
                            <div className={`h-1.5 rounded-full ${
                              (equipmentData.power.current_load_kw / equipmentData.power.max_load_kw) > 0.8 ? 'bg-red-500' :
                              (equipmentData.power.current_load_kw / equipmentData.power.max_load_kw) > 0.6 ? 'bg-yellow-500' : 'bg-green-500'
                            }`} style={{ width: `${(equipmentData.power.current_load_kw / equipmentData.power.max_load_kw) * 100}%` }} />
                          </div>
                          <span className="text-gray-300">{equipmentData.power.current_load_kw.toFixed(1)}kW</span>
                        </div>
                      </div>
                      <div>
                        <p className="text-gray-500">Grid Voltage</p>
                        <p className="text-gray-300">{equipmentData.power.grid_voltage.toFixed(0)}V</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Battery Health</p>
                        <p className={equipmentData.power.battery_health_percent < 80 ? 'text-yellow-400' : 'text-green-400'}>
                          {equipmentData.power.battery_health_percent.toFixed(0)}%
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Battery Backup</p>
                        <p className="text-gray-300">{equipmentData.power.battery_backup_hours.toFixed(0)} hours</p>
                      </div>
                      <div>
                        <p className="text-gray-500">UPS Status</p>
                        <p className={equipmentData.power.ups_status === 'online' ? 'text-green-400' : 'text-yellow-400'}>
                          {equipmentData.power.ups_status}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Efficiency</p>
                        <p className="text-gray-300">{equipmentData.power.power_efficiency_percent.toFixed(0)}%</p>
                      </div>
                      {equipmentData.power.generator_status !== 'not_installed' && (
                        <>
                          <div>
                            <p className="text-gray-500">Generator</p>
                            <p className={equipmentData.power.generator_status === 'standby' ? 'text-green-400' : 'text-yellow-400'}>
                              {equipmentData.power.generator_status}
                            </p>
                          </div>
                          {equipmentData.power.generator_fuel_level_percent !== null && (
                            <div>
                              <p className="text-gray-500">Fuel Level</p>
                              <p className={equipmentData.power.generator_fuel_level_percent < 30 ? 'text-yellow-400' : 'text-gray-300'}>
                                {equipmentData.power.generator_fuel_level_percent.toFixed(0)}%
                              </p>
                            </div>
                          )}
                        </>
                      )}
                      <div>
                        <p className="text-gray-500">Outages YTD</p>
                        <p className={equipmentData.power.total_outages_ytd > 3 ? 'text-yellow-400' : 'text-gray-300'}>
                          {equipmentData.power.total_outages_ytd}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Status with Reason */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-2">Current Status</h3>
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-5 h-5 text-blue-500" />
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                node.status === 'healthy' ? 'bg-green-600 text-white' :
                node.status === 'degraded' ? 'bg-yellow-600 text-white' :
                node.status === 'outage' ? 'bg-red-600 text-white' :
                'bg-gray-600 text-white'
              }`}>
                {node.status.toUpperCase()}
              </span>
            </div>
            {/* Show reason for degradation/outage */}
            {(node.status === 'degraded' || node.status === 'outage') && activeAlerts.length > 0 && (
              <div className={`mt-2 p-3 rounded-lg border ${
                node.status === 'outage' ? 'bg-red-900/20 border-red-600' : 'bg-yellow-900/20 border-yellow-600'
              }`}>
                <p className={`text-sm font-medium ${node.status === 'outage' ? 'text-red-400' : 'text-yellow-400'}`}>
                  Why is this node {node.status}?
                </p>
                <ul className="mt-1 space-y-1">
                  {activeAlerts.slice(0, 3).map((alert) => (
                    <li key={alert.alert_id} className="text-xs text-gray-300 flex items-start gap-2">
                      <span className="text-gray-500">•</span>
                      <span>{alert.description || `${alert.alert_type.replace(/_/g, ' ')} detected`}</span>
                    </li>
                  ))}
                </ul>
                {activeAlerts.length > 3 && (
                  <p className="text-xs text-gray-500 mt-1">+{activeAlerts.length - 3} more issues</p>
                )}
              </div>
            )}
          </div>

          {/* Recommended Actions for Critical Nodes */}
          {(node.status === 'degraded' || node.status === 'outage') && (
            <div>
              <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                <Zap className="w-4 h-4 text-yellow-500" />
                Recommended Actions
              </h3>
              <div className="space-y-2">
                {activeActions.length > 0 ? (
                  <div className="bg-blue-900/20 border border-blue-600 rounded-lg p-3">
                    <p className="text-xs text-blue-400 font-medium mb-2">🔄 Automated remediation in progress</p>
                    <p className="text-sm text-gray-300">
                      {activeActions[0].action_type.replace(/_/g, ' ')} - {activeActions[0].status}
                    </p>
                  </div>
                ) : (
                  <div className="bg-gray-700 rounded-lg p-3 border border-gray-600 space-y-2">
                    <p className="text-xs text-gray-400 font-medium">Suggested manual actions:</p>
                    {node.status === 'outage' ? (
                      <>
                        <div className="flex items-center gap-2 text-sm text-gray-300">
                          <span className="w-5 h-5 flex items-center justify-center bg-red-600 rounded text-xs text-white font-bold">1</span>
                          <span>Dispatch field crew for physical inspection</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-gray-300">
                          <span className="w-5 h-5 flex items-center justify-center bg-red-600 rounded text-xs text-white font-bold">2</span>
                          <span>Check fiber backhaul connectivity</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-gray-300">
                          <span className="w-5 h-5 flex items-center justify-center bg-red-600 rounded text-xs text-white font-bold">3</span>
                          <span>Verify power supply ({node.power_supply_status || 'unknown'})</span>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="flex items-center gap-2 text-sm text-gray-300">
                          <span className="w-5 h-5 flex items-center justify-center bg-yellow-600 rounded text-xs text-white font-bold">1</span>
                          <span>Review KPI metrics for anomalies</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-gray-300">
                          <span className="w-5 h-5 flex items-center justify-center bg-yellow-600 rounded text-xs text-white font-bold">2</span>
                          <span>Consider load balancing to neighbor nodes</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-gray-300">
                          <span className="w-5 h-5 flex items-center justify-center bg-yellow-600 rounded text-xs text-white font-bold">3</span>
                          <span>Check firmware version ({node.firmware_version || 'unknown'})</span>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Active Issues - Always shown */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <AlertTriangle className={`w-4 h-4 ${activeAlerts.length > 0 ? 'text-orange-500' : 'text-gray-500'}`} />
              Active Issues ({activeAlerts.length})
            </h3>
            {activeAlerts.length > 0 ? (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {activeAlerts.map((alert) => (
                  <div
                    key={alert.alert_id}
                    className="bg-gray-700 rounded-lg p-3 border border-gray-600"
                  >
                    <div className="flex items-start justify-between mb-1">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        alert.severity === 'critical' ? 'bg-red-600 text-white' :
                        alert.severity === 'warning' ? 'bg-yellow-600 text-white' :
                        'bg-blue-600 text-white'
                      }`}>
                        {alert.severity.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-400">
                        {formatTimestamp(alert.timestamp)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-200 mb-1">{alert.description}</p>
                    {alert.root_cause && (
                      <p className="text-xs text-gray-400">
                        Root cause: {alert.root_cause}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-green-900/20 border border-green-600/50 rounded-lg p-3">
                <p className="text-sm text-green-400 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" />
                  No active issues - node is operating normally
                </p>
              </div>
            )}
          </div>

          {/* Self-Healing Progress - Always shown */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Wrench className={`w-4 h-4 ${recentAction ? 'text-blue-500' : 'text-gray-500'}`} />
              Self-Healing Progress
            </h3>
            {recentAction ? (
              <div className="bg-gray-700 rounded-lg p-4 border border-gray-600">
                {/* Action Type */}
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm text-gray-300">
                    {recentAction.action_type.replace(/_/g, ' ').toUpperCase()}
                  </span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(recentAction.status)}`}>
                    {recentAction.status.replace(/_/g, ' ').toUpperCase()}
                  </span>
                </div>

                {/* Progress Bar */}
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-400">Progress</span>
                    <span className="text-xs font-semibold text-blue-400">
                      {Math.round(overallProgress)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-600 rounded-full h-2.5">
                    <div
                      className={`h-2.5 rounded-full transition-all duration-300 ${
                        recentAction.status === 'completed' ? 'bg-green-500' :
                        recentAction.status === 'failed' ? 'bg-red-500' :
                        'bg-blue-500'
                      }`}
                      style={{ width: `${overallProgress}%` }}
                    ></div>
                  </div>
                </div>

                {/* Stage Information */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      recentAction.status === 'pending' ? 'bg-gray-400 animate-pulse' : 'bg-green-500'
                    }`}></div>
                    <span className="text-xs text-gray-300">Initialized</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      recentAction.status === 'in_progress' ? 'bg-blue-400 animate-pulse' :
                      recentAction.status === 'completed' || recentAction.status === 'failed' ? 'bg-green-500' :
                      'bg-gray-600'
                    }`}></div>
                    <span className="text-xs text-gray-300">Executing Remediation</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      recentAction.status === 'completed' ? 'bg-green-500' :
                      recentAction.status === 'failed' ? 'bg-red-500' :
                      'bg-gray-600'
                    }`}></div>
                    <span className="text-xs text-gray-300">
                      {recentAction.status === 'completed' ? 'Completed' :
                       recentAction.status === 'failed' ? 'Failed' :
                       'Pending Completion'}
                    </span>
                  </div>
                </div>

                {/* Timestamps */}
                <div className="mt-3 pt-3 border-t border-gray-600 text-xs text-gray-400">
                  <div className="flex justify-between">
                    <span>Started: {formatTimestamp(recentAction.timestamp)}</span>
                    {recentAction.completion_time && (
                      <span>Completed: {formatTimestamp(recentAction.completion_time)}</span>
                    )}
                  </div>
                  {recentAction.effectiveness_score && (
                    <div className="mt-1">
                      Effectiveness: {recentAction.effectiveness_score}%
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-gray-700 rounded-lg p-4 border border-gray-600">
                <p className="text-sm text-gray-400 text-center">No self-healing actions in progress</p>
              </div>
            )}
          </div>

          {/* Healing Statistics - Always shown */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Clock className={`w-4 h-4 ${totalActions > 0 ? 'text-purple-500' : 'text-gray-500'}`} />
              Healing Statistics
            </h3>
            <div className="bg-gray-700 rounded-lg p-4 border border-gray-600">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold text-white">{totalActions}</p>
                  <p className="text-xs text-gray-400">Total Actions</p>
                </div>
                <div>
                  <p className={`text-2xl font-bold ${totalActions > 0 ? 'text-green-400' : 'text-gray-500'}`}>
                    {totalActions > 0 ? `${successRate.toFixed(0)}%` : 'N/A'}
                  </p>
                  <p className="text-xs text-gray-400">Success Rate</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-blue-400">
                    {avgResolutionTime > 0 ? formatDuration(Math.round(avgResolutionTime)) : 'N/A'}
                  </p>
                  <p className="text-xs text-gray-400">Avg Resolution</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-gray-600">
                <div className="flex items-center gap-1 justify-center">
                  <CheckCircle2 className="w-3 h-3 text-green-500" />
                  <span className="text-xs text-gray-300">{completedActions.length} completed</span>
                </div>
                <div className="flex items-center gap-1 justify-center">
                  <XCircle className="w-3 h-3 text-red-500" />
                  <span className="text-xs text-gray-300">{failedActions.length} failed</span>
                </div>
                <div className="flex items-center gap-1 justify-center">
                  <Clock className="w-3 h-3 text-blue-500" />
                  <span className="text-xs text-gray-300">{activeActions.length} active</span>
                </div>
              </div>
            </div>
          </div>

          {/* Resolved Alerts - Always shown */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <CheckCircle2 className={`w-4 h-4 ${resolvedAlerts.length > 0 ? 'text-green-500' : 'text-gray-500'}`} />
              Recently Resolved ({resolvedAlerts.length})
            </h3>
            {resolvedAlerts.length > 0 ? (
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {resolvedAlerts.slice(0, 5).map((alert) => (
                  <div
                    key={alert.alert_id}
                    className="bg-gray-700 rounded-lg p-3 border border-gray-600"
                  >
                    <div className="flex items-start justify-between mb-1">
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-600 text-white">
                        RESOLVED
                      </span>
                      <span className="text-xs text-gray-400">
                        {alert.resolved_at && formatTimestamp(alert.resolved_at)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-300">{alert.description}</p>
                    {alert.resolved_at && (
                      <p className="text-xs text-gray-500 mt-1">
                        Resolved in {formatDuration(Math.round((alert.resolved_at.getTime() - alert.timestamp.getTime()) / 1000))}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-gray-700 rounded-lg p-3 border border-gray-600">
                <p className="text-sm text-gray-400 text-center">No resolved alerts in recent history</p>
              </div>
            )}
          </div>

          {/* Action History - Always shown */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
                <Wrench className={`w-4 h-4 ${actions.length > 0 ? 'text-gray-400' : 'text-gray-500'}`} />
                Action History ({actions.length})
              </h3>
              {actions.length > 3 && (
                <button
                  onClick={() => setShowAllActions(!showAllActions)}
                  className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                >
                  {showAllActions ? 'Show Less' : 'Show All'}
                </button>
              )}
            </div>
            {actions.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {(showAllActions ? actions : actions.slice(0, 3)).map((action) => (
                  <div
                    key={action.action_id}
                    className="bg-gray-700 rounded-lg p-3 border border-gray-600"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-gray-300">
                        {action.action_type.replace(/_/g, ' ').toUpperCase()}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(action.status)}`}>
                        {action.status.replace(/_/g, ' ').toUpperCase()}
                      </span>
                    </div>
                    <div className="text-xs text-gray-400 space-y-1">
                      <div>Started: {formatTimestamp(action.timestamp)}</div>
                      {action.completion_time && (
                        <div>
                          Completed: {formatTimestamp(action.completion_time)}
                          {' '}({formatDuration(Math.round((action.completion_time.getTime() - action.timestamp.getTime()) / 1000))})
                        </div>
                      )}
                      {action.effectiveness_score && (
                        <div>Effectiveness: {action.effectiveness_score}%</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-gray-700 rounded-lg p-3 border border-gray-600">
                <p className="text-sm text-gray-400 text-center">No action history available</p>
              </div>
            )}
          </div>

          {/* Equipment Information */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Server className="w-4 h-4 text-cyan-500" />
              Equipment Information
            </h3>
            <div className="bg-gray-700 rounded-lg p-4 border border-gray-600">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400">Manufacturer</p>
                  <p className="text-sm font-medium text-white">{node.manufacturer || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Hardware Model</p>
                  <p className="text-sm font-medium text-white">{node.hardware_model || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Firmware Version</p>
                  <p className="text-sm font-mono text-white">{node.firmware_version || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">DOCSIS Version</p>
                  <p className="text-sm font-mono text-white">{node.docsis_version || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Node Type</p>
                  <p className="text-sm font-medium text-white">{node.node_type || 'N/A'}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Plant & Infrastructure */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Building2 className="w-4 h-4 text-purple-500" />
              Plant & Infrastructure
            </h3>
            <div className="bg-gray-700 rounded-lg p-4 border border-gray-600">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400">Headend</p>
                  <p className="text-sm font-medium text-white">{node.headend_id || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Hub</p>
                  <p className="text-sm font-medium text-white">{node.hub_id || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Service Area</p>
                  <p className="text-sm font-medium text-white">{node.service_area || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Amplifier Cascade</p>
                  <p className="text-sm font-medium text-white">{node.amplifier_cascade ?? 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Coax Plant</p>
                  <p className="text-sm font-medium text-white">{node.coax_plant_miles ? `${node.coax_plant_miles.toFixed(1)} miles` : 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Fiber Miles</p>
                  <p className="text-sm font-medium text-white">{node.fiber_miles ? `${node.fiber_miles.toFixed(1)} miles` : 'N/A'}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Location & Geographic */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <MapPin className="w-4 h-4 text-green-500" />
              Location & Geographic
            </h3>
            <div className="bg-gray-700 rounded-lg p-4 border border-gray-600">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400">Coordinates</p>
                  <p className="text-sm font-mono text-white">
                    {node.latitude.toFixed(4)}, {node.longitude.toFixed(4)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">City</p>
                  <p className="text-sm font-medium text-white">{node.city || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">State</p>
                  <p className="text-sm font-medium text-white">{node.state || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Region</p>
                  <p className="text-sm font-medium text-white">{node.region}</p>
                </div>
              </div>
            </div>
          </div>

          {/* RF Configuration */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Signal className="w-4 h-4 text-blue-500" />
              RF Channel Configuration
            </h3>
            <div className="bg-gray-700 rounded-lg p-4 border border-gray-600">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400">Downstream Channels</p>
                  <p className="text-sm font-medium text-white">{node.downstream_channels ?? 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Upstream Channels</p>
                  <p className="text-sm font-medium text-white">{node.upstream_channels ?? 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">OFDM Channels</p>
                  <p className="text-sm font-medium text-white">{node.ofdm_channels ?? 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">OFDMA Channels</p>
                  <p className="text-sm font-medium text-white">{node.ofdma_channels ?? 'N/A'}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Service Coverage */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Radio className="w-4 h-4 text-yellow-500" />
              Service Coverage
            </h3>
            <div className="bg-gray-700 rounded-lg p-4 border border-gray-600">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400">DOCSIS Version</p>
                  <div className="flex gap-1 mt-1">
                    <span className="px-2 py-0.5 bg-blue-600 text-white text-xs font-medium rounded">
                      {node.docsis_version || 'N/A'}
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Coax Plant Miles</p>
                  <p className="text-sm font-medium text-white">{node.coax_plant_miles ? `${node.coax_plant_miles.toFixed(1)} mi` : 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Homes Active / Passed</p>
                  <p className="text-sm font-medium text-white">{formatNumber(node.homes_active || 0)} / {formatNumber(node.homes_passed || 0)}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Network Connectivity */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Network className="w-4 h-4 text-orange-500" />
              Network Connectivity
            </h3>
            <div className="bg-gray-700 rounded-lg p-4 border border-gray-600">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400">Headend</p>
                  <p className="text-sm font-medium text-white">{node.headend_id || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Hub</p>
                  <p className="text-sm font-medium text-white">{node.hub_id || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Fiber Miles</p>
                  <p className="text-sm font-medium text-white">{node.fiber_miles ? `${node.fiber_miles.toFixed(1)} mi` : 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Neighbor Nodes</p>
                  <p className="text-sm font-medium text-white">{(node.neighbor_nodes || []).length}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Power & Energy */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Zap className="w-4 h-4 text-yellow-500" />
              Power & Energy
            </h3>
            <div className="bg-gray-700 rounded-lg p-4 border border-gray-600">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400">Power Supply Status</p>
                  <p className="text-sm font-medium text-white">{node.power_supply_status || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Power Supply Count</p>
                  <p className="text-sm font-medium text-white">{node.power_supply_count ?? 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Battery Backup</p>
                  <p className="text-sm font-medium text-white">{node.battery_backup_hours != null ? `${node.battery_backup_hours.toFixed(1)} hours` : 'N/A'}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Operational Details */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Settings className="w-4 h-4 text-gray-500" />
              Operational Details
            </h3>
            <div className="bg-gray-700 rounded-lg p-4 border border-gray-600">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400">Node Type</p>
                  <p className="text-sm font-medium text-white">{node.node_type || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Service Area</p>
                  <p className="text-sm font-medium text-white">{node.service_area || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Priority</p>
                  <p className="text-sm font-medium text-white">{(node.homes_active || 0) > 500 ? 'Critical' : (node.homes_active || 0) > 200 ? 'Standard' : 'Basic'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Homes Passed</p>
                  <p className="text-sm font-medium text-white">{node.homes_passed ?? 'N/A'}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Maintenance */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-pink-500" />
              Maintenance History
            </h3>
            <div className="bg-gray-700 rounded-lg p-4 border border-gray-600">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400">Commissioned</p>
                  <p className="text-sm font-medium text-white">
                    {node.commissioned_date ? formatTimestamp(node.commissioned_date) : 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Last Maintenance</p>
                  <p className="text-sm font-medium text-white">
                    {node.last_maintenance ? formatTimestamp(node.last_maintenance) : 'N/A'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Neighbor Nodes */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3">
              Neighbor Nodes ({(node.neighbor_nodes || []).length})
            </h3>
            <div className="flex flex-wrap gap-2">
              {(node.neighbor_nodes || []).slice(0, 10).map((neighborId) => (
                <span
                  key={neighborId}
                  className="px-2 py-1 bg-gray-700 text-gray-300 text-xs rounded border border-gray-600"
                >
                  {neighborId}
                </span>
              ))}
              {(node.neighbor_nodes || []).length > 10 && (
                <span className="px-2 py-1 text-gray-500 text-xs">
                  +{(node.neighbor_nodes || []).length - 10} more
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 px-6 py-4 border-t border-gray-200">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
});

NodeDetailModal.displayName = 'NodeDetailModal';

export default NodeDetailModal;
