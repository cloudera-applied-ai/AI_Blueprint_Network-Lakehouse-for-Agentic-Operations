import { memo, useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  PlayCircle,
  BarChart3,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingDown,
  TrendingUp,
  Server,
  Activity,
  RefreshCw,
  Loader2,
  ChevronDown,
  Globe,
  Network,
  Settings,
  Shield,
  Cpu,
  HardDrive,
  Radio,
  Satellite,
  Cable,
  Brain,
  MessageSquare,
  Layers,
  CircleDot,
  ArrowRight,
  Sparkles,
  Trash2,
  Square,
  CheckSquare,
} from 'lucide-react';
import {
  runSimulation,
  getSimulationResults,
  getSimulationHistoricalContext,
  startAgenticCapacityPlanning,
  getAgenticCapacityPlanningStatus,
  getNodeMetadataSummary,
  getDatacenterMetadataSummary,
  getDatacenters,
  deleteSimulationResult,
  deleteSimulationResultsBatch,
  type SimulationResult,
  type RunSimulationRequest,
  type SimulationHistoricalContext,
  type CapacityForecast,
  type BandwidthBottleneck,
  type AgenticCapacityPlanningRequest,
  type AgenticCapacityPlanningStatus,
  type NodeMetadataSummary,
  type DatacenterMetadataSummary,
  type DatacenterResponse,
} from '@/services/apiClient';
import { Database, History } from 'lucide-react';

interface ScenarioOption {
  type: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  gradient: string;
}

const scenarioOptions: ScenarioOption[] = [
  {
    type: 'failure',
    name: 'Node Failure',
    description: 'Simulate random node failures',
    icon: <Server className="w-5 h-5" />,
    gradient: 'from-red-500/20 to-red-600/10',
  },
  {
    type: 'capacity',
    name: 'Capacity Surge',
    description: 'Peak traffic simulation',
    icon: <TrendingUp className="w-5 h-5" />,
    gradient: 'from-amber-500/20 to-amber-600/10',
  },
  {
    type: 'maintenance',
    name: 'Maintenance',
    description: 'Scheduled downtime',
    icon: <Clock className="w-5 h-5" />,
    gradient: 'from-blue-500/20 to-blue-600/10',
  },
  {
    type: 'disaster',
    name: 'Disaster',
    description: 'Regional outage scenario',
    icon: <AlertTriangle className="w-5 h-5" />,
    gradient: 'from-rose-500/20 to-rose-600/10',
  },
  {
    type: 'capacity_planning',
    name: 'AI Planning',
    description: 'Agentic capacity analysis',
    icon: <Brain className="w-5 h-5" />,
    gradient: 'from-cyan-500/20 to-purple-600/10',
  },
];

// Default region options - will be replaced with data-driven options when metadata loads
const defaultRegionOptions = [
  { value: '', label: 'All Regions' },
  { value: 'NORTH_AMERICA', label: 'North America' },
  { value: 'SOUTH_AMERICA', label: 'South America' },
  { value: 'EUROPE', label: 'Europe' },
  { value: 'ASIA', label: 'Asia' },
  { value: 'AFRICA', label: 'Africa' },
  { value: 'OCEANIA', label: 'Oceania' },
];

const nodeTypeOptions = [
  { value: '5G', label: '5G NR' },
  { value: 'LTE', label: 'LTE/4G' },
  { value: '3G', label: '3G/UMTS' },
];

const formatCurrency = (value: number): string => {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(2)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
};

const formatPercent = (value: number): string => `${value.toFixed(1)}%`;

// Professional Card Component
interface CardProps {
  children: React.ReactNode;
  className?: string;
  gradient?: boolean;
  hover?: boolean;
}

const Card = memo(({ children, className = '', gradient = false, hover = false }: CardProps) => (
  <div className={`
    relative overflow-hidden rounded-2xl
    ${gradient ? 'bg-gradient-to-br from-slate-800/80 to-slate-900/80' : 'bg-slate-800/60'}
    backdrop-blur-xl border border-slate-700/50
    ${hover ? 'hover:border-slate-600/50 hover:shadow-lg hover:shadow-slate-900/20 transition-all duration-300' : ''}
    ${className}
  `}>
    {children}
  </div>
));

Card.displayName = 'Card';

// Section Header Component
interface SectionHeaderProps {
  icon: React.ReactNode;
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

const SectionHeader = memo(({ icon, title, subtitle, action }: SectionHeaderProps) => (
  <div className="flex items-center justify-between mb-4">
    <div className="flex items-center gap-3">
      <div className="p-2 rounded-xl bg-gradient-to-br from-slate-700/50 to-slate-800/50 border border-slate-600/30">
        {icon}
      </div>
      <div>
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        {subtitle && <p className="text-sm text-slate-400">{subtitle}</p>}
      </div>
    </div>
    {action}
  </div>
));

SectionHeader.displayName = 'SectionHeader';

// Collapsible Section Component
interface CollapsibleSectionProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: string;
}

const CollapsibleSection = memo(({ title, icon, children, defaultOpen = false, badge }: CollapsibleSectionProps) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="rounded-xl overflow-hidden border border-slate-700/50 bg-slate-800/40">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-4 flex items-center justify-between hover:bg-slate-700/30 transition-all duration-200"
      >
        <div className="flex items-center gap-3">
          <span className="text-slate-400">{icon}</span>
          <span className="text-white font-medium">{title}</span>
          {badge && (
            <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
              {badge}
            </span>
          )}
        </div>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      <div className={`overflow-hidden transition-all duration-300 ${isOpen ? 'max-h-[1000px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="p-4 pt-0 space-y-4 border-t border-slate-700/50">
          {children}
        </div>
      </div>
    </div>
  );
});

CollapsibleSection.displayName = 'CollapsibleSection';

// Metric Card Component
interface MetricCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  color?: 'cyan' | 'green' | 'amber' | 'red' | 'purple' | 'blue';
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
}

const MetricCard = memo(({ label, value, subValue, color = 'cyan', trend, icon }: MetricCardProps) => {
  const colorClasses = {
    cyan: 'text-cyan-400',
    green: 'text-emerald-400',
    amber: 'text-amber-400',
    red: 'text-red-400',
    purple: 'text-purple-400',
    blue: 'text-blue-400',
  };

  const bgClasses = {
    cyan: 'from-cyan-500/10 to-cyan-600/5',
    green: 'from-emerald-500/10 to-emerald-600/5',
    amber: 'from-amber-500/10 to-amber-600/5',
    red: 'from-red-500/10 to-red-600/5',
    purple: 'from-purple-500/10 to-purple-600/5',
    blue: 'from-blue-500/10 to-blue-600/5',
  };

  return (
    <div className={`relative p-4 rounded-xl bg-gradient-to-br ${bgClasses[color]} border border-slate-700/50 overflow-hidden`}>
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</span>
          {icon && <span className={colorClasses[color]}>{icon}</span>}
        </div>
        <div className="flex items-end gap-2">
          <span className={`text-2xl font-bold ${colorClasses[color]}`}>{value}</span>
          {trend && (
            <span className={`mb-1 ${trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-slate-400'}`}>
              {trend === 'up' ? <TrendingUp className="w-4 h-4" /> : trend === 'down' ? <TrendingDown className="w-4 h-4" /> : null}
            </span>
          )}
        </div>
        {subValue && <div className="mt-1 text-xs text-slate-500">{subValue}</div>}
      </div>
      <div className={`absolute -right-4 -bottom-4 w-24 h-24 rounded-full bg-gradient-to-br ${bgClasses[color]} opacity-50 blur-2xl`} />
    </div>
  );
});

MetricCard.displayName = 'MetricCard';

// Status Badge Component
interface StatusBadgeProps {
  status: 'success' | 'warning' | 'error' | 'info' | 'neutral';
  label: string;
  pulse?: boolean;
}

const StatusBadge = memo(({ status, label, pulse = false }: StatusBadgeProps) => {
  const colors = {
    success: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    warning: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    error: 'bg-red-500/20 text-red-400 border-red-500/30',
    info: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    neutral: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg border ${colors[status]}`}>
      {pulse && <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${status === 'success' ? 'bg-emerald-400' : status === 'error' ? 'bg-red-400' : 'bg-amber-400'}`} />}
      {label}
    </span>
  );
});

StatusBadge.displayName = 'StatusBadge';

// Professional Report Components
interface ReportSectionProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

const ReportSection = memo(({ title, children, className = '' }: ReportSectionProps) => (
  <div className={`mb-6 ${className}`}>
    <h3 className="text-base font-semibold text-slate-200 border-b border-slate-600/50 pb-2 mb-4 uppercase tracking-wide">
      {title}
    </h3>
    {children}
  </div>
));

ReportSection.displayName = 'ReportSection';

interface DataTableProps {
  headers: string[];
  rows: (string | number | React.ReactNode)[][];
  className?: string;
}

const DataTable = memo(({ headers, rows, className = '' }: DataTableProps) => (
  <div className={`overflow-x-auto ${className}`}>
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-slate-600/50">
          {headers.map((header, idx) => (
            <th key={idx} className="text-left py-2 px-3 text-slate-400 font-medium text-xs uppercase tracking-wider">
              {header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, rowIdx) => (
          <tr key={rowIdx} className="border-b border-slate-700/30 hover:bg-slate-800/30">
            {row.map((cell, cellIdx) => (
              <td key={cellIdx} className="py-2.5 px-3 text-slate-300">
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
));

DataTable.displayName = 'DataTable';

interface KeyValueRowProps {
  label: string;
  value: string | number | React.ReactNode;
  highlight?: boolean;
}

const KeyValueRow = memo(({ label, value, highlight = false }: KeyValueRowProps) => (
  <div className="flex justify-between items-center py-2 border-b border-slate-700/30 last:border-0">
    <span className="text-slate-400 text-sm">{label}</span>
    <span className={`font-medium ${highlight ? 'text-cyan-400' : 'text-slate-200'}`}>{value}</span>
  </div>
));

KeyValueRow.displayName = 'KeyValueRow';

interface SeverityIndicatorProps {
  level: 'low' | 'medium' | 'high' | 'critical';
}

const SeverityIndicator = memo(({ level }: SeverityIndicatorProps) => {
  const config = {
    low: { color: 'bg-green-500', label: 'Low' },
    medium: { color: 'bg-yellow-500', label: 'Medium' },
    high: { color: 'bg-orange-500', label: 'High' },
    critical: { color: 'bg-red-500', label: 'Critical' },
  };
  const { color, label } = config[level] || config.low;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`w-2 h-2 rounded-full ${color}`} />
      <span className="text-slate-300 text-sm">{label}</span>
    </span>
  );
});

SeverityIndicator.displayName = 'SeverityIndicator';

// Simulation Result Card Component
interface SimulationResultCardProps {
  result: SimulationResult;
  expanded: boolean;
  onToggle: () => void;
}

const SimulationResultCard = memo(({ result, expanded, onToggle }: SimulationResultCardProps) => {
  const baseline = result.baseline_metrics;
  const simulated = result.simulated_metrics;
  const isCapacityPlanning = simulated.scenario_type === 'capacity_planning';
  const scenario = scenarioOptions.find(s => s.type === result.simulated_metrics.scenario_type);

  return (
    <div className="border-b border-slate-700/30 last:border-0">
      <button
        onClick={onToggle}
        className="w-full px-5 py-3 flex items-center justify-between hover:bg-slate-700/20 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-slate-400">{scenario?.icon || <Activity className="w-4 h-4" />}</span>
          <div>
            <div className="text-sm text-white font-medium">{scenario?.name || result.simulated_metrics.scenario_type}</div>
            <div className="text-xs text-slate-500 flex items-center gap-2">
              {!isCapacityPlanning && <span>{result.affected_node_count} nodes</span>}
              <span>{new Date(result.created_at).toLocaleString()}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {isCapacityPlanning ? (
            <div className="text-right">
              <div className="text-sm font-semibold text-cyan-400">{simulated.growth_rate_percent_per_month?.toFixed(1) || 0}%</div>
              <div className="text-xs text-slate-500">growth/mo</div>
            </div>
          ) : (
            <div className="text-right">
              <div className="text-sm font-semibold text-red-400">{formatCurrency(result.projected_revenue_loss)}</div>
              <div className="text-xs text-slate-500">loss</div>
            </div>
          )}
          <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {expanded && (
        <div className="px-5 pb-4 space-y-4 border-t border-slate-700/30 bg-slate-900/20">
          {baseline.data_source && (
            <div className="pt-3 flex items-center gap-2 text-xs text-slate-500">
              <Database className="w-3 h-3" />
              <span>Source: {baseline.data_source}</span>
            </div>
          )}

          {isCapacityPlanning ? (
            <>
              <div className="grid grid-cols-4 gap-4 pt-3 text-sm">
                <div>
                  <div className="text-slate-500 text-xs">Trend</div>
                  <div className="text-white font-medium">{(simulated.trend_direction || 'stable').toUpperCase()}</div>
                </div>
                <div>
                  <div className="text-slate-500 text-xs">Node Util</div>
                  <div className="text-white font-medium">{simulated.current_node_utilization?.toFixed(1) || 0}%</div>
                </div>
                <div>
                  <div className="text-slate-500 text-xs">DC Util</div>
                  <div className="text-white font-medium">{simulated.current_dc_utilization?.toFixed(1) || 0}%</div>
                </div>
                <div>
                  <div className="text-slate-500 text-xs">Throughput</div>
                  <div className="text-white font-medium">{simulated.total_throughput_gbps?.toFixed(1) || 0} Gbps</div>
                </div>
              </div>

              {simulated.forecasts && Array.isArray(simulated.forecasts) && simulated.forecasts.length > 0 && (
                <div className="pt-3">
                  <div className="text-xs text-slate-500 mb-2">Capacity Forecast</div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-slate-700/30">
                          <th className="text-left py-1.5 text-slate-400 font-medium">Period</th>
                          <th className="text-left py-1.5 text-slate-400 font-medium">Utilization</th>
                          <th className="text-left py-1.5 text-slate-400 font-medium">Bandwidth</th>
                          <th className="text-left py-1.5 text-slate-400 font-medium">Risk</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(simulated.forecasts as CapacityForecast[]).map((forecast) => (
                          <tr key={forecast.period_days} className="border-b border-slate-700/20">
                            <td className="py-1.5 text-slate-300">{forecast.period_days} days</td>
                            <td className="py-1.5 text-slate-300">{forecast.projected_node_utilization?.toFixed(0)}%</td>
                            <td className="py-1.5 text-slate-300">{forecast.projected_bandwidth_usage_gbps?.toFixed(1)} Gbps</td>
                            <td className="py-1.5">
                              <SeverityIndicator level={forecast.risk_level as 'low' | 'medium' | 'high' | 'critical'} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {simulated.bandwidth_bottlenecks && Array.isArray(simulated.bandwidth_bottlenecks) && simulated.bandwidth_bottlenecks.length > 0 && (
                <div className="pt-3">
                  <div className="text-xs text-red-400 flex items-center gap-1.5 mb-2">
                    <AlertTriangle className="w-3 h-3" />
                    Bottlenecks ({(simulated.bandwidth_bottlenecks as BandwidthBottleneck[]).length})
                  </div>
                  <div className="space-y-1">
                    {(simulated.bandwidth_bottlenecks as BandwidthBottleneck[]).map((bottleneck, idx) => (
                      <div key={idx} className="flex items-center justify-between text-xs p-2 bg-slate-800/30 rounded">
                        <span className="text-slate-300">{bottleneck.location}</span>
                        <div className="flex items-center gap-3">
                          <span className={bottleneck.current_utilization >= 90 ? 'text-red-400' : 'text-amber-400'}>
                            {bottleneck.current_utilization?.toFixed(1)}%
                          </span>
                          {bottleneck.projected_breach_days && (
                            <span className="text-slate-500">breach in {bottleneck.projected_breach_days}d</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <>
              <div className="pt-3">
                <div className="text-xs text-slate-500 mb-2">Metric Comparison (Baseline → Simulated)</div>
                <div className="grid grid-cols-4 gap-3 text-xs">
                  <div className="p-2 bg-slate-800/30 rounded">
                    <div className="text-slate-400 mb-1">Uptime</div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-emerald-400">{formatPercent(baseline.uptime_percent)}</span>
                      <ArrowRight className="w-3 h-3 text-slate-500" />
                      <span className="text-red-400">{formatPercent(simulated.uptime_percent)}</span>
                    </div>
                  </div>
                  <div className="p-2 bg-slate-800/30 rounded">
                    <div className="text-slate-400 mb-1">Latency</div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-emerald-400">{baseline.latency_ms?.toFixed(0) || 0}ms</span>
                      <ArrowRight className="w-3 h-3 text-slate-500" />
                      <span className="text-red-400">{simulated.latency_ms?.toFixed(0) || 0}ms</span>
                    </div>
                  </div>
                  <div className="p-2 bg-slate-800/30 rounded">
                    <div className="text-slate-400 mb-1">Throughput</div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-emerald-400">{baseline.throughput_mbps?.toFixed(0) || 0}</span>
                      <ArrowRight className="w-3 h-3 text-slate-500" />
                      <span className="text-red-400">{simulated.throughput_mbps?.toFixed(0) || 0}</span>
                    </div>
                  </div>
                  <div className="p-2 bg-slate-800/30 rounded">
                    <div className="text-slate-400 mb-1">Packet Loss</div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-emerald-400">{formatPercent(baseline.packet_loss_percent || 0)}</span>
                      <ArrowRight className="w-3 h-3 text-slate-500" />
                      <span className="text-red-400">{formatPercent(simulated.packet_loss_percent || 0)}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 text-sm">
                <div className="p-2 bg-slate-800/30 rounded text-center">
                  <div className="text-red-400 font-semibold">{result.risk_score.toFixed(0)}%</div>
                  <div className="text-xs text-slate-500">SLA Risk</div>
                </div>
                <div className="p-2 bg-slate-800/30 rounded text-center">
                  <div className="text-amber-400 font-semibold">{(simulated.capacity_utilization || 0).toFixed(0)}%</div>
                  <div className="text-xs text-slate-500">Capacity</div>
                </div>
                <div className="p-2 bg-slate-800/30 rounded text-center">
                  <div className="text-white font-semibold">{(simulated.users_affected || 0).toLocaleString()}</div>
                  <div className="text-xs text-slate-500">Users Affected</div>
                </div>
              </div>
            </>
          )}

          {(result.recommended_actions || []).length > 0 && (
            <div className="pt-3">
              <div className="text-xs text-slate-500 mb-2">Recommendations</div>
              <div className="space-y-1.5">
                {(result.recommended_actions || []).slice(0, 3).map((rec: { action: string; priority: number }, idx: number) => (
                  <div key={idx} className="flex items-start gap-2 text-xs">
                    <CheckCircle className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                    <span className="text-slate-300">{rec.action}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

SimulationResultCard.displayName = 'SimulationResultCard';

// Agent definitions for the status panel
const agentDefinitions = [
  { id: 'data-collector', name: 'Collector', icon: HardDrive, color: 'text-blue-400', bgColor: 'from-blue-500/20 to-blue-600/10' },
  { id: 'upgrade-analyzer', name: 'Analyzer', icon: TrendingUp, color: 'text-emerald-400', bgColor: 'from-emerald-500/20 to-emerald-600/10' },
  { id: 'hardware-checker', name: 'Hardware', icon: Cpu, color: 'text-amber-400', bgColor: 'from-amber-500/20 to-amber-600/10' },
  { id: 'dc-component-analyzer', name: 'DC Analysis', icon: Server, color: 'text-purple-400', bgColor: 'from-purple-500/20 to-purple-600/10' },
  { id: 'capacity-forecaster', name: 'Forecaster', icon: Brain, color: 'text-cyan-400', bgColor: 'from-cyan-500/20 to-cyan-600/10' },
];

// Backhaul type options for capacity planning
const backhaulTypeOptions = [
  { value: 'Fiber', label: 'Fiber', icon: Cable, color: 'text-emerald-400', description: 'High capacity, low latency' },
  { value: 'Starlink', label: 'Starlink', icon: Satellite, color: 'text-blue-400', description: 'Quick deploy, moderate latency' },
  { value: 'Microwave', label: 'Microwave', icon: Radio, color: 'text-amber-400', description: 'Point-to-point, medium capacity' },
];

// Agent Status Panel Component
interface AgentStatusPanelProps {
  execution: AgenticCapacityPlanningStatus;
}

const AgentStatusPanel = memo(({ execution }: AgentStatusPanelProps) => {
  const thoughtsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    thoughtsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [execution.thoughts]);

  const getAgentProgress = (agentId: string) => {
    const agentThoughts = execution.thoughts.filter(t => t.agent_id === agentId);
    if (agentThoughts.length === 0) return 'pending';
    if (execution.current_agent === agentId) return 'active';
    return 'completed';
  };

  const getThoughtIcon = (type: string) => {
    switch (type) {
      case 'thought': return <MessageSquare className="w-3 h-3" />;
      case 'tool_call': return <Cpu className="w-3 h-3" />;
      case 'tool_result': return <CheckCircle className="w-3 h-3" />;
      case 'data': return <HardDrive className="w-3 h-3" />;
      case 'analysis': return <Brain className="w-3 h-3" />;
      case 'error': return <AlertTriangle className="w-3 h-3" />;
      default: return <Activity className="w-3 h-3" />;
    }
  };

  const getThoughtColor = (type: string) => {
    switch (type) {
      case 'thought': return 'text-slate-400';
      case 'tool_call': return 'text-blue-400';
      case 'tool_result': return 'text-emerald-400';
      case 'data': return 'text-cyan-400';
      case 'analysis': return 'text-purple-400';
      case 'error': return 'text-red-400';
      default: return 'text-slate-400';
    }
  };

  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-700/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-slate-700/50">
            <Brain className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">Analysis in Progress</h3>
            <p className="text-xs text-slate-400">
              {execution.current_agent_name ? `Running: ${execution.current_agent_name}` : 'Initializing...'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-2xl font-bold text-cyan-400 font-mono">{execution.progress_percent.toFixed(0)}%</div>
            <div className="text-xs text-slate-500">complete</div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="px-5 py-3 bg-slate-900/30">
        <div className="w-full h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
          <div
            className="h-full bg-cyan-500 transition-all duration-500 ease-out"
            style={{ width: `${execution.progress_percent}%` }}
          />
        </div>
      </div>

      {/* Agent Pipeline - Simplified */}
      <div className="px-5 py-3 border-b border-slate-700/50">
        <div className="flex items-center gap-1">
          {agentDefinitions.map((agent, idx) => {
            const status = getAgentProgress(agent.id);
            const Icon = agent.icon;
            return (
              <div key={agent.id} className="flex items-center flex-1">
                <div className="flex flex-col items-center gap-1 flex-1">
                  <div
                    className={`p-2 rounded-lg transition-all duration-300 ${
                      status === 'active'
                        ? 'bg-cyan-500/20 border border-cyan-500/50'
                        : status === 'completed'
                        ? 'bg-emerald-500/20 border border-emerald-500/50'
                        : 'bg-slate-700/30 border border-slate-600/30'
                    }`}
                  >
                    <Icon
                      className={`w-3.5 h-3.5 ${
                        status === 'active'
                          ? 'text-cyan-400'
                          : status === 'completed'
                          ? 'text-emerald-400'
                          : 'text-slate-500'
                      }`}
                    />
                  </div>
                  <span className={`text-[9px] font-medium ${status === 'active' ? 'text-cyan-400' : status === 'completed' ? 'text-emerald-400' : 'text-slate-500'}`}>
                    {agent.name}
                  </span>
                </div>
                {idx < agentDefinitions.length - 1 && (
                  <div className={`h-px flex-1 mx-1 ${
                    status === 'completed' ? 'bg-emerald-500/50' : 'bg-slate-700/50'
                  }`} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Activity Log - Compact */}
      <div className="max-h-40 overflow-y-auto">
        <div className="px-5 py-2 space-y-1">
          {execution.thoughts.slice(-10).map((thought) => (
            <div key={thought.id} className="flex items-start gap-2 text-xs py-1">
              <span className={`mt-0.5 flex-shrink-0 ${getThoughtColor(thought.type)}`}>
                {getThoughtIcon(thought.type)}
              </span>
              <span className="text-slate-500 font-mono flex-shrink-0">[{thought.agent_name}]</span>
              <span className="text-slate-400 truncate">{thought.content}</span>
            </div>
          ))}
          <div ref={thoughtsEndRef} />
          {execution.thoughts.length === 0 && (
            <div className="text-center text-slate-500 text-xs py-4">
              <Loader2 className="w-4 h-4 mx-auto mb-1 animate-spin" />
              Initializing agents...
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

AgentStatusPanel.displayName = 'AgentStatusPanel';

// Main Component
const DigitalTwinView = memo(() => {
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [results, setResults] = useState<SimulationResult[]>([]);
  const [currentResult, setCurrentResult] = useState<SimulationResult | null>(null);
  const [expandedResult, setExpandedResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Selection state for batch delete
  const [selectedResultIds, setSelectedResultIds] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);

  const [historicalContext, setHistoricalContext] = useState<SimulationHistoricalContext | null>(null);
  const [loadingContext, setLoadingContext] = useState(false);
  const [showHistoricalContext, setShowHistoricalContext] = useState(false);

  const [selectedScenario, setSelectedScenario] = useState<string>('failure');

  const [affectedPercent, setAffectedPercent] = useState<number>(5);
  const [durationHours, setDurationHours] = useState<number>(2);
  const [surgeFactor, setSurgeFactor] = useState<number>(1.5);
  const [severity, setSeverity] = useState<number>(0.5);

  const [agenticExecution, setAgenticExecution] = useState<AgenticCapacityPlanningStatus | null>(null);
  const [analysisMode, setAnalysisMode] = useState<'current_state' | 'upgrade_scenario' | 'add_redundancy'>('current_state');
  const [targetBackhaulType, setTargetBackhaulType] = useState<'Fiber' | 'Starlink' | 'Microwave'>('Fiber');
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Node metadata from database
  const [nodeMetadata, setNodeMetadata] = useState<NodeMetadataSummary | null>(null);

  // Datacenter metadata and filters for AI Planning
  const [datacenterMetadata, setDatacenterMetadata] = useState<DatacenterMetadataSummary | null>(null);
  const [selectedCity, setSelectedCity] = useState<string>('');
  const [selectedDatacenter, setSelectedDatacenter] = useState<string>('');
  const [availableCities, setAvailableCities] = useState<{ value: string; count: number }[]>([]);
  const [availableDatacenters, setAvailableDatacenters] = useState<DatacenterResponse[]>([]);
  const [selectedForecastPeriods, setSelectedForecastPeriods] = useState<number[]>([30, 60, 90]);

  const [selectedRegion, setSelectedRegion] = useState<string>('');
  const [selectedNodeTypes, setSelectedNodeTypes] = useState<string[]>([]);
  const [timeOfDay, setTimeOfDay] = useState<string>('normal');
  const [cascadingFailure, setCascadingFailure] = useState<boolean>(false);
  const [recoveryStrategy, setRecoveryStrategy] = useState<string>('manual');
  const [customSlaUptime, setCustomSlaUptime] = useState<number>(99.9);
  const [customSlaLatency, setCustomSlaLatency] = useState<number>(50);
  const [backhaulCapacity, setBackhaulCapacity] = useState<number>(100);
  const [datacenterLatency, setDatacenterLatency] = useState<number>(0);
  const [networkCongestion, setNetworkCongestion] = useState<number>(1.0);
  const [packetLoss, setPacketLoss] = useState<number>(0);

  const loadHistory = useCallback(async () => {
    try {
      setLoadingHistory(true);
      const response = await getSimulationResults({ limit: 10 });
      setResults(response.items);
    } catch (err) {
      console.error('Failed to load simulation history:', err);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // Fetch node metadata on mount
  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const metadata = await getNodeMetadataSummary();
        setNodeMetadata(metadata);
      } catch (err) {
        console.error('Failed to fetch node metadata:', err);
      }
    };
    fetchMetadata();
  }, []);

  // Fetch datacenter metadata on mount
  useEffect(() => {
    const fetchDCMetadata = async () => {
      try {
        const metadata = await getDatacenterMetadataSummary();
        setDatacenterMetadata(metadata);
      } catch (err) {
        console.error('Failed to fetch datacenter metadata:', err);
      }
    };
    fetchDCMetadata();
  }, []);

  // Update available cities when region changes (cascading filter)
  useEffect(() => {
    if (datacenterMetadata && selectedRegion) {
      // Filter cities by selected region from the metadata
      const citiesInRegion = datacenterMetadata.cities.filter(c => c.region === selectedRegion);
      setAvailableCities(citiesInRegion);
      // Reset city and datacenter selection when region changes
      setSelectedCity('');
      setSelectedDatacenter('');
      setAvailableDatacenters([]);
    } else {
      // Clear cities when no region selected
      setAvailableCities([]);
      setSelectedCity('');
      setSelectedDatacenter('');
      setAvailableDatacenters([]);
    }
  }, [selectedRegion, datacenterMetadata]);

  // Update available datacenters when city or region changes (cascading filter)
  useEffect(() => {
    const fetchDatacenters = async () => {
      if (selectedCity) {
        try {
          const response = await getDatacenters({ city: selectedCity, limit: 100 });
          setAvailableDatacenters(response.items);
          // Reset datacenter selection when city changes
          setSelectedDatacenter('');
        } catch (err) {
          console.error('Failed to fetch datacenters:', err);
          setAvailableDatacenters([]);
        }
      } else if (selectedRegion) {
        // Fetch all datacenters in the region if no city selected
        try {
          const response = await getDatacenters({ region: selectedRegion, limit: 100 });
          setAvailableDatacenters(response.items);
          setSelectedDatacenter('');
        } catch (err) {
          console.error('Failed to fetch datacenters:', err);
          setAvailableDatacenters([]);
        }
      } else {
        setAvailableDatacenters([]);
        setSelectedDatacenter('');
      }
    };
    fetchDatacenters();
  }, [selectedCity, selectedRegion]);

  const loadHistoricalContext = useCallback(async () => {
    try {
      setLoadingContext(true);
      const nodesAffected = Math.max(1, Math.floor(2000 * affectedPercent / 100));
      const context = await getSimulationHistoricalContext(selectedScenario, nodesAffected, 168);
      setHistoricalContext(context);
    } catch (err) {
      console.error('Failed to load historical context:', err);
    } finally {
      setLoadingContext(false);
    }
  }, [selectedScenario, affectedPercent]);

  useEffect(() => {
    if (showHistoricalContext) {
      loadHistoricalContext();
    }
  }, [showHistoricalContext, loadHistoricalContext]);

  const toggleNodeType = (type: string) => {
    setSelectedNodeTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    );
  };

  // Compute region options from metadata or use defaults
  const regionOptions = useMemo(() => {
    if (nodeMetadata?.regions && nodeMetadata.regions.length > 0) {
      const formatRegionLabel = (value: string) => {
        return value.split('_').map(word =>
          word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
        ).join(' ');
      };
      return [
        { value: '', label: 'All Regions' },
        ...nodeMetadata.regions.map(r => ({
          value: r.value,
          label: `${formatRegionLabel(r.value)} (${r.count.toLocaleString()})`
        }))
      ];
    }
    return defaultRegionOptions;
  }, [nodeMetadata]);

  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  const pollAgenticStatus = useCallback(async (executionId: string) => {
    try {
      const status = await getAgenticCapacityPlanningStatus(executionId);
      setAgenticExecution(status);

      if (status.status === 'completed' || status.status === 'failed') {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        setLoading(false);
      }
    } catch (err) {
      console.error('Failed to poll agentic status:', err);
    }
  }, []);

  const runAgenticCapacityPlanning = async () => {
    try {
      setLoading(true);
      setError(null);
      setAgenticExecution(null);

      const request: AgenticCapacityPlanningRequest = {
        analysis_mode: analysisMode,
        target_upgrade_type: analysisMode !== 'current_state' ? targetBackhaulType : undefined,
        region: selectedRegion || undefined,
        city: selectedCity || undefined,
        datacenter_ids: selectedDatacenter ? [selectedDatacenter] : undefined,
        forecast_periods: selectedForecastPeriods.length > 0 ? selectedForecastPeriods : undefined,
        include_cost_estimate: true,
      };

      const response = await startAgenticCapacityPlanning(request);

      pollAgenticStatus(response.execution_id);
      pollingRef.current = setInterval(() => {
        pollAgenticStatus(response.execution_id);
      }, 1500);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start agentic analysis');
      setLoading(false);
    }
  };

  const runSelectedSimulation = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: Record<string, unknown> = {
        affected_percent: affectedPercent,
        duration_hours: durationHours,
        time_of_day: timeOfDay,
        cascading_failure: cascadingFailure,
        recovery_strategy: recoveryStrategy,
        custom_sla_uptime: customSlaUptime,
        custom_sla_latency: customSlaLatency,
        backhaul_capacity_percent: backhaulCapacity,
        datacenter_latency_ms: datacenterLatency,
        network_congestion_factor: networkCongestion,
        packet_loss_percent: packetLoss,
      };

      if (selectedRegion) params.region = selectedRegion;
      if (selectedNodeTypes.length > 0) params.node_types = selectedNodeTypes;
      if (selectedScenario === 'capacity') params.surge_factor = surgeFactor;
      else if (selectedScenario === 'disaster') params.severity = severity;

      const request: RunSimulationRequest = {
        scenario_type: selectedScenario,
        parameters: params,
      };

      const result = await runSimulation(request);
      setCurrentResult(result);
      setResults(prev => [result, ...prev]);
      setExpandedResult(result.result_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  // Delete handlers
  const handleDeleteResult = async (resultId: string) => {
    try {
      setIsDeleting(true);
      await deleteSimulationResult(resultId);
      setResults(prev => prev.filter(r => r.result_id !== resultId));
      setSelectedResultIds(prev => {
        const next = new Set(prev);
        next.delete(resultId);
        return next;
      });
      if (expandedResult === resultId) {
        setExpandedResult(null);
      }
    } catch (err) {
      console.error('Failed to delete result:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete result');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedResultIds.size === 0) return;
    try {
      setIsDeleting(true);
      const idsToDelete = Array.from(selectedResultIds);
      await deleteSimulationResultsBatch(idsToDelete);
      setResults(prev => prev.filter(r => !selectedResultIds.has(r.result_id)));
      setSelectedResultIds(new Set());
      if (expandedResult && selectedResultIds.has(expandedResult)) {
        setExpandedResult(null);
      }
    } catch (err) {
      console.error('Failed to delete results:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete results');
    } finally {
      setIsDeleting(false);
    }
  };

  const toggleResultSelection = (resultId: string) => {
    setSelectedResultIds(prev => {
      const next = new Set(prev);
      if (next.has(resultId)) {
        next.delete(resultId);
      } else {
        next.add(resultId);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedResultIds.size === results.length) {
      setSelectedResultIds(new Set());
    } else {
      setSelectedResultIds(new Set(results.map(r => r.result_id)));
    }
  };

  return (
    <div className="min-h-screen space-y-6">
      {/* Professional Header */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-lg bg-slate-700/50">
              <Layers className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Network Capacity Planning</h1>
              <p className="text-slate-400 text-sm mt-0.5">
                AI-powered simulation and analysis platform
              </p>
            </div>
          </div>
          {nodeMetadata && (
            <div className="hidden md:flex items-center gap-6 text-sm">
              <div className="text-right">
                <div className="text-slate-400">Total Nodes</div>
                <div className="text-white font-semibold">{nodeMetadata.total_nodes.toLocaleString()}</div>
              </div>
              <div className="h-8 w-px bg-slate-700" />
              <div className="text-right">
                <div className="text-slate-400">Regions</div>
                <div className="text-white font-semibold">{nodeMetadata.regions.length}</div>
              </div>
              <div className="h-8 w-px bg-slate-700" />
              <div className="text-right">
                <div className="text-slate-400">Node Types</div>
                <div className="text-white font-semibold">{nodeMetadata.node_types.length}</div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Controls Panel */}
        <div className="lg:col-span-4 space-y-4">
          {/* Scenario Selection */}
          <Card gradient className="p-5">
            <SectionHeader
              icon={<Sparkles className="w-5 h-5 text-cyan-400" />}
              title="Scenario Type"
              subtitle="Select simulation mode"
            />
            <div className="grid grid-cols-2 gap-2">
              {scenarioOptions.map(option => (
                <button
                  key={option.type}
                  onClick={() => setSelectedScenario(option.type)}
                  className={`relative p-3 rounded-xl border transition-all duration-200 text-left overflow-hidden group ${
                    selectedScenario === option.type
                      ? 'bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 border-cyan-500/50 shadow-lg shadow-cyan-500/10'
                      : 'bg-slate-800/40 border-slate-700/50 hover:border-slate-600/50 hover:bg-slate-700/30'
                  }`}
                >
                  <div className={`absolute inset-0 bg-gradient-to-br ${option.gradient} opacity-0 group-hover:opacity-100 transition-opacity`} />
                  <div className="relative z-10">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={selectedScenario === option.type ? 'text-cyan-400' : 'text-slate-400'}>{option.icon}</span>
                      <span className="text-white text-sm font-medium">{option.name}</span>
                    </div>
                    <div className="text-slate-400 text-xs">{option.description}</div>
                  </div>
                </button>
              ))}
            </div>
          </Card>

          {/* Scrollable Controls */}
          <div className="space-y-3 max-h-[calc(100vh-400px)] overflow-y-auto pr-1 custom-scrollbar">
            {/* Capacity Planning Parameters */}
            {selectedScenario === 'capacity_planning' && (
              <CollapsibleSection
                title="AI Planning Options"
                icon={<Brain className="w-4 h-4 text-cyan-400" />}
                defaultOpen={true}
                badge="NEW"
              >
                <div>
                  <label className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2 block">Analysis Mode</label>
                  <div className="space-y-2">
                    {[
                      { value: 'current_state', label: 'Current State', desc: 'Analyze existing capacity', icon: <CircleDot className="w-4 h-4" /> },
                      { value: 'upgrade_scenario', label: 'Upgrade Scenario', desc: 'Plan connection upgrades', icon: <TrendingUp className="w-4 h-4" /> },
                      { value: 'add_redundancy', label: 'Add Redundancy', desc: 'Plan backup connections', icon: <Shield className="w-4 h-4" /> },
                    ].map(mode => (
                      <button
                        key={mode.value}
                        onClick={() => setAnalysisMode(mode.value as typeof analysisMode)}
                        className={`w-full p-3 rounded-xl text-left transition-all duration-200 flex items-center gap-3 ${
                          analysisMode === mode.value
                            ? 'bg-gradient-to-r from-cyan-500/20 to-purple-500/10 border border-cyan-500/50'
                            : 'bg-slate-800/40 border border-slate-700/50 hover:border-slate-600/50'
                        }`}
                      >
                        <span className={analysisMode === mode.value ? 'text-cyan-400' : 'text-slate-500'}>{mode.icon}</span>
                        <div className="flex-1">
                          <div className="text-white text-sm font-medium">{mode.label}</div>
                          <div className="text-slate-400 text-xs">{mode.desc}</div>
                        </div>
                        {analysisMode === mode.value && <CheckCircle className="w-4 h-4 text-cyan-400" />}
                      </button>
                    ))}
                  </div>
                </div>

                {analysisMode !== 'current_state' && (
                  <div>
                    <label className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2 block">Target Connection</label>
                    <div className="grid grid-cols-3 gap-2">
                      {backhaulTypeOptions.map(opt => {
                        const Icon = opt.icon;
                        return (
                          <button
                            key={opt.value}
                            onClick={() => setTargetBackhaulType(opt.value as typeof targetBackhaulType)}
                            className={`p-3 rounded-xl text-center transition-all duration-200 ${
                              targetBackhaulType === opt.value
                                ? 'bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 border border-emerald-500/50'
                                : 'bg-slate-800/40 border border-slate-700/50 hover:border-slate-600/50'
                            }`}
                          >
                            <Icon className={`w-5 h-5 mx-auto mb-1.5 ${targetBackhaulType === opt.value ? 'text-emerald-400' : opt.color}`} />
                            <div className="text-white text-xs font-medium">{opt.label}</div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Location Filters (Cascading) - Uses datacenter regions */}
                <div>
                  <label className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2 block">Location Filters</label>
                  <div className="space-y-3">
                    {/* Region Dropdown - uses datacenter regions for AI Planning */}
                    <div>
                      <label className="text-xs text-slate-500 mb-1 block">Region</label>
                      <select
                        value={selectedRegion}
                        onChange={(e) => setSelectedRegion(e.target.value)}
                        className="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                      >
                        <option value="">All Regions</option>
                        {datacenterMetadata?.regions.map(r => (
                          <option key={r.value} value={r.value}>{r.value} ({r.count} DCs)</option>
                        ))}
                      </select>
                      {!datacenterMetadata && (
                        <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                          <Loader2 className="w-3 h-3 animate-spin" /> Loading regions...
                        </p>
                      )}
                    </div>

                    {/* City Dropdown (cascading from region) */}
                    <div>
                      <label className="text-xs text-slate-500 mb-1 block">City</label>
                      <select
                        value={selectedCity}
                        onChange={(e) => setSelectedCity(e.target.value)}
                        className="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50 disabled:opacity-50"
                        disabled={!selectedRegion || availableCities.length === 0}
                      >
                        <option value="">{selectedRegion ? (availableCities.length === 0 ? 'No cities found' : 'All Cities in Region') : 'Select a region first'}</option>
                        {availableCities.map(c => (
                          <option key={c.value} value={c.value}>{c.value} ({c.count} DCs)</option>
                        ))}
                      </select>
                    </div>

                    {/* Datacenter Dropdown (cascading from region/city) */}
                    <div>
                      <label className="text-xs text-slate-500 mb-1 block">Datacenter</label>
                      <select
                        value={selectedDatacenter}
                        onChange={(e) => setSelectedDatacenter(e.target.value)}
                        className="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50 disabled:opacity-50"
                        disabled={!selectedRegion || availableDatacenters.length === 0}
                      >
                        <option value="">{selectedRegion ? (availableDatacenters.length === 0 ? 'No datacenters found' : `All Datacenters${selectedCity ? ' in City' : ' in Region'}`) : 'Select a region first'}</option>
                        {availableDatacenters.map(dc => (
                          <option key={dc.headend_id} value={dc.headend_id}>{dc.name} - {dc.city} ({dc.status})</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Forecast Periods */}
                <div>
                  <label className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2 block">Forecast Periods</label>
                  <div className="flex flex-wrap gap-2">
                    {[30, 60, 90, 180, 365].map(days => {
                      const isSelected = selectedForecastPeriods.includes(days);
                      const label = days === 365 ? '1yr' : `${days}d`;
                      return (
                        <button
                          key={days}
                          onClick={() => {
                            if (isSelected) {
                              setSelectedForecastPeriods(prev => prev.filter(d => d !== days));
                            } else {
                              setSelectedForecastPeriods(prev => [...prev, days].sort((a, b) => a - b));
                            }
                          }}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                            isSelected
                              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50'
                              : 'bg-slate-700/50 text-slate-400 border border-slate-600/50 hover:border-slate-500/50'
                          }`}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                  <p className="text-xs text-slate-500 mt-1.5">
                    {selectedForecastPeriods.length === 0
                      ? 'Select at least one period'
                      : `Forecasting: ${selectedForecastPeriods.map(d => d === 365 ? '1 year' : `${d} days`).join(', ')}`}
                  </p>
                </div>

                {/* Network Infrastructure Summary */}
                <div>
                  <label className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2 block">Current Network Infrastructure</label>
                  {nodeMetadata ? (
                    <div className="space-y-2">
                      <div className="grid grid-cols-2 gap-2">
                        {nodeMetadata.node_types.map(bt => (
                          <div
                            key={bt.value}
                            className="px-3 py-2 rounded-lg bg-slate-700/30 border border-slate-600/30"
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-medium text-slate-300">{bt.value}</span>
                              <span className="text-xs font-bold text-cyan-400">{bt.count.toLocaleString()}</span>
                            </div>
                            <div className="mt-1 h-1 bg-slate-700 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full"
                                style={{ width: `${(bt.count / nodeMetadata.total_nodes) * 100}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-slate-500 mt-2">
                        {nodeMetadata.total_nodes.toLocaleString()} total nodes across {nodeMetadata.node_types.length} node types
                      </p>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-slate-500 text-xs">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Loading infrastructure data...
                    </div>
                  )}
                </div>
              </CollapsibleSection>
            )}

            {/* Basic Parameters */}
            <CollapsibleSection
              title="Basic Parameters"
              icon={<Settings className="w-4 h-4 text-blue-400" />}
              defaultOpen={selectedScenario !== 'capacity_planning'}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-slate-400">Affected Nodes</label>
                  <span className="text-sm font-bold text-cyan-400">{affectedPercent}%</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="50"
                  value={affectedPercent}
                  onChange={(e) => setAffectedPercent(Number(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-slate-400">Duration</label>
                  <span className="text-sm font-bold text-cyan-400">{durationHours} hours</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="24"
                  value={durationHours}
                  onChange={(e) => setDurationHours(Number(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                />
              </div>

              {selectedScenario === 'capacity' && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-medium text-slate-400">Surge Factor</label>
                    <span className="text-sm font-bold text-amber-400">{surgeFactor.toFixed(1)}x</span>
                  </div>
                  <input
                    type="range"
                    min="1.1"
                    max="3"
                    step="0.1"
                    value={surgeFactor}
                    onChange={(e) => setSurgeFactor(Number(e.target.value))}
                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-500"
                  />
                </div>
              )}

              {selectedScenario === 'disaster' && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-medium text-slate-400">Severity</label>
                    <span className="text-sm font-bold text-red-400">{(severity * 100).toFixed(0)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="1"
                    step="0.1"
                    value={severity}
                    onChange={(e) => setSeverity(Number(e.target.value))}
                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-red-500"
                  />
                </div>
              )}
            </CollapsibleSection>

            {/* Region & Node Type */}
            <CollapsibleSection title="Region & Node Type" icon={<Globe className="w-4 h-4 text-emerald-400" />}>
              <div>
                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2 block">Region</label>
                <select
                  value={selectedRegion}
                  onChange={(e) => setSelectedRegion(e.target.value)}
                  className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all"
                >
                  {regionOptions.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2 block">Node Technologies</label>
                <div className="flex flex-wrap gap-2">
                  {nodeTypeOptions.map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => toggleNodeType(opt.value)}
                      className={`px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                        selectedNodeTypes.includes(opt.value)
                          ? 'bg-blue-500/20 text-blue-300 border border-blue-500/50'
                          : 'bg-slate-700/50 text-slate-400 border border-slate-600/50 hover:border-slate-500/50'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            </CollapsibleSection>

            {/* Time & Recovery */}
            <CollapsibleSection title="Time & Recovery" icon={<Clock className="w-4 h-4 text-amber-400" />}>
              <div>
                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2 block">Time of Day</label>
                <div className="grid grid-cols-3 gap-2">
                  {['off_peak', 'normal', 'peak'].map(time => (
                    <button
                      key={time}
                      onClick={() => setTimeOfDay(time)}
                      className={`px-3 py-2 rounded-xl text-xs font-medium transition-all duration-200 ${
                        timeOfDay === time
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/50'
                          : 'bg-slate-700/50 text-slate-400 border border-slate-600/50 hover:border-slate-500/50'
                      }`}
                    >
                      {time === 'off_peak' ? 'Off-Peak' : time === 'normal' ? 'Normal' : 'Peak'}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2 block">Recovery Strategy</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { value: 'manual', label: 'Manual', color: 'amber' },
                    { value: 'ai_assisted', label: 'AI-Assisted', color: 'purple' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => setRecoveryStrategy(opt.value)}
                      className={`px-3 py-2 rounded-xl text-xs font-medium transition-all duration-200 ${
                        recoveryStrategy === opt.value
                          ? opt.color === 'purple'
                            ? 'bg-purple-500/20 text-purple-300 border border-purple-500/50'
                            : 'bg-amber-500/20 text-amber-300 border border-amber-500/50'
                          : 'bg-slate-700/50 text-slate-400 border border-slate-600/50 hover:border-slate-500/50'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-800/40 border border-slate-700/50">
                <div>
                  <div className="text-sm font-medium text-white">Cascading Failures</div>
                  <div className="text-xs text-slate-400">Model failure propagation</div>
                </div>
                <button
                  onClick={() => setCascadingFailure(!cascadingFailure)}
                  className={`relative w-12 h-6 rounded-full transition-colors duration-300 ${
                    cascadingFailure ? 'bg-red-500' : 'bg-slate-600'
                  }`}
                >
                  <div className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-300 ${
                    cascadingFailure ? 'translate-x-7' : 'translate-x-1'
                  }`} />
                </button>
              </div>
            </CollapsibleSection>

            {/* Custom SLA */}
            <CollapsibleSection title="SLA Thresholds" icon={<Shield className="w-4 h-4 text-purple-400" />}>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-slate-400">Uptime Target</label>
                  <span className="text-sm font-bold text-purple-400">{customSlaUptime.toFixed(1)}%</span>
                </div>
                <input
                  type="range"
                  min="95"
                  max="99.99"
                  step="0.1"
                  value={customSlaUptime}
                  onChange={(e) => setCustomSlaUptime(Number(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-slate-400">Max Latency</label>
                  <span className="text-sm font-bold text-purple-400">{customSlaLatency}ms</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="200"
                  step="5"
                  value={customSlaLatency}
                  onChange={(e) => setCustomSlaLatency(Number(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
                />
              </div>
            </CollapsibleSection>

            {/* Network Connectivity */}
            <CollapsibleSection title="Network Parameters" icon={<Network className="w-4 h-4 text-cyan-400" />}>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-slate-400">Backhaul Capacity</label>
                  <span className="text-sm font-bold text-cyan-400">{backhaulCapacity}%</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="100"
                  value={backhaulCapacity}
                  onChange={(e) => setBackhaulCapacity(Number(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-slate-400">DC Latency Offset</label>
                  <span className="text-sm font-bold text-cyan-400">+{datacenterLatency}ms</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={datacenterLatency}
                  onChange={(e) => setDatacenterLatency(Number(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-slate-400">Network Congestion</label>
                  <span className="text-sm font-bold text-cyan-400">{networkCongestion.toFixed(1)}x</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="3"
                  step="0.1"
                  value={networkCongestion}
                  onChange={(e) => setNetworkCongestion(Number(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-slate-400">Packet Loss</label>
                  <span className="text-sm font-bold text-red-400">{packetLoss}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="20"
                  step="0.5"
                  value={packetLoss}
                  onChange={(e) => setPacketLoss(Number(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-red-500"
                />
              </div>
            </CollapsibleSection>
          </div>

          {/* Run Button */}
          <button
            onClick={selectedScenario === 'capacity_planning' ? runAgenticCapacityPlanning : runSelectedSimulation}
            disabled={loading}
            className={`w-full py-4 rounded-xl text-white font-semibold flex items-center justify-center gap-3 transition-all duration-300 shadow-lg ${
              selectedScenario === 'capacity_planning'
                ? 'bg-gradient-to-r from-cyan-600 to-purple-600 hover:from-cyan-500 hover:to-purple-500 shadow-cyan-500/20 disabled:from-slate-600 disabled:to-slate-600'
                : 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 shadow-blue-500/20 disabled:from-slate-600 disabled:to-slate-600'
            }`}
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>{selectedScenario === 'capacity_planning' ? 'Running AI Analysis...' : 'Simulating...'}</span>
              </>
            ) : (
              <>
                {selectedScenario === 'capacity_planning' ? (
                  <>
                    <Brain className="w-5 h-5" />
                    <span>Run AI Analysis</span>
                    <Sparkles className="w-4 h-4" />
                  </>
                ) : (
                  <>
                    <PlayCircle className="w-5 h-5" />
                    <span>Run Simulation</span>
                  </>
                )}
              </>
            )}
          </button>

          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-red-400 font-medium">Error</div>
                <div className="text-sm text-slate-400">{error}</div>
              </div>
            </div>
          )}
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-8 space-y-4">
          {/* Historical Context - Collapsible */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
            <button
              onClick={() => setShowHistoricalContext(!showHistoricalContext)}
              className="w-full px-5 py-3 flex items-center justify-between hover:bg-slate-700/20 transition-colors"
            >
              <div className="flex items-center gap-3">
                <History className="w-4 h-4 text-slate-400" />
                <span className="text-sm font-medium text-slate-300">Historical Context</span>
                <span className="text-xs text-slate-500">7-day baselines</span>
              </div>
              <div className="flex items-center gap-3">
                {historicalContext && (
                  <span className={`text-xs px-2 py-0.5 rounded ${historicalContext.confidence_score >= 0.8 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                    {(historicalContext.confidence_score * 100).toFixed(0)}% confidence
                  </span>
                )}
                <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${showHistoricalContext ? 'rotate-180' : ''}`} />
              </div>
            </button>

            {showHistoricalContext && (
              <div className="px-5 pb-4 border-t border-slate-700/50">
                {loadingContext ? (
                  <div className="flex items-center justify-center py-6">
                    <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                    <span className="ml-2 text-sm text-slate-400">Loading...</span>
                  </div>
                ) : historicalContext ? (
                  <div className="pt-4 space-y-4">
                    <div className="grid grid-cols-4 gap-4 text-sm">
                      <div>
                        <div className="text-slate-500 text-xs">Avg Latency</div>
                        <div className="text-white font-medium">{(historicalContext.baselines.kpi_baselines.latency_ms || 25).toFixed(1)} ms</div>
                      </div>
                      <div>
                        <div className="text-slate-500 text-xs">DS SNR</div>
                        <div className="text-white font-medium">{(historicalContext.baselines.kpi_baselines.ds_snr_db || 36).toFixed(1)} dB</div>
                      </div>
                      <div>
                        <div className="text-slate-500 text-xs">Throughput</div>
                        <div className="text-white font-medium">{(historicalContext.baselines.kpi_baselines.throughput_mbps || 150).toFixed(0)} Mbps</div>
                      </div>
                      <div>
                        <div className="text-slate-500 text-xs">Avg MTTR</div>
                        <div className="text-white font-medium">{historicalContext.baselines.incident_baselines.mttr_minutes?.toFixed(0) || '30'} min</div>
                      </div>
                    </div>

                    {historicalContext.similar_incidents.length > 0 && (
                      <div className="pt-3 border-t border-slate-700/30">
                        <div className="text-xs text-slate-500 mb-2">Similar Past Incidents</div>
                        <div className="space-y-1.5">
                          {historicalContext.similar_incidents.slice(0, 3).map((incident, idx) => (
                            <div key={idx} className="flex items-center justify-between text-xs p-2 bg-slate-900/30 rounded">
                              <span className="text-slate-300">{incident.action_type?.replace(/_/g, ' ')}</span>
                              <div className="flex items-center gap-3">
                                <span className="text-slate-400">{incident.duration_minutes?.toFixed(0) || '-'} min</span>
                                {incident.effectiveness_score !== null && (
                                  <span className={`${incident.effectiveness_score >= 80 ? 'text-emerald-400' : incident.effectiveness_score >= 60 ? 'text-amber-400' : 'text-red-400'}`}>
                                    {incident.effectiveness_score.toFixed(0)}%
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-4 text-sm text-slate-500">
                    No historical context available
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Agentic Execution */}
          {agenticExecution && (
            <div className="space-y-4">
              <AgentStatusPanel execution={agenticExecution} />

              {agenticExecution.status === 'completed' && agenticExecution.result && (
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
                  {/* Report Header */}
                  <div className="bg-slate-900/80 border-b border-slate-700/50 px-8 py-6">
                    <div className="flex justify-between items-start">
                      <div>
                        <h1 className="text-xl font-light tracking-wide text-slate-400">NETWORK CAPACITY</h1>
                        <h2 className="text-2xl font-bold text-white">Analysis Report</h2>
                      </div>
                      <div className="text-right text-sm">
                        <div className="text-slate-400">Report Generated</div>
                        <div className="font-semibold text-white">{new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</div>
                        <div className="text-slate-500 text-xs mt-1">ID: {agenticExecution.execution_id?.slice(0, 8) || 'N/A'}</div>
                      </div>
                    </div>
                  </div>

                  {/* Executive Summary Banner */}
                  {agenticExecution.result.analysis_summary && (
                    <div className="bg-cyan-500/10 border-l-4 border-cyan-500 px-8 py-5">
                      <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-wider mb-2">Executive Summary</h3>
                      {/* Use datacenter_analysis regional data if available */}
                      {agenticExecution.datacenter_analysis?.issues_by_location &&
                       Object.values(agenticExecution.datacenter_analysis.issues_by_location).some(issues => (issues as string[]).length > 0) ? (
                        <div className="space-y-4">
                          {(() => {
                            const dcAnalysis = agenticExecution.datacenter_analysis!;
                            const issuesByLocation = dcAnalysis.issues_by_location || {};
                            const healthByLocation = dcAnalysis.health_by_location || {};
                            const growthByLocation = dcAnalysis.growth_by_location || {};

                            // Count total critical issues
                            const totalIssues = Object.values(issuesByLocation).reduce((sum, issues) => sum + (issues as string[]).length, 0);

                            // Sort locations by number of issues (descending)
                            const sortedLocations = Object.keys(issuesByLocation)
                              .filter(loc => (issuesByLocation[loc] as string[]).length > 0)
                              .sort((a, b) => (issuesByLocation[b] as string[]).length - (issuesByLocation[a] as string[]).length);

                            return (
                              <div className="space-y-4">
                                <p className="text-slate-300 text-sm">
                                  <span className="text-red-400 font-semibold">{totalIssues} issues</span> identified across {sortedLocations.length} locations requiring attention.
                                </p>

                                {sortedLocations.map(location => {
                                  const issues = issuesByLocation[location] as string[];
                                  const health = healthByLocation[location] || 0;
                                  const growth = growthByLocation[location] || {};
                                  const criticalCount = growth.critical_count || 0;
                                  const avgGrowth = growth.avg_growth_per_week || 0;

                                  return (
                                    <div key={location} className="bg-slate-900/50 rounded-lg overflow-hidden">
                                      <div className="bg-slate-800/80 px-4 py-2 flex items-center justify-between">
                                        <h4 className="font-semibold text-white flex items-center gap-2">
                                          <Globe className="w-4 h-4 text-slate-400" />
                                          {location}
                                        </h4>
                                        <div className="flex items-center gap-3 text-xs">
                                          <span className={`px-2 py-0.5 rounded ${
                                            health >= 90 ? 'bg-emerald-500/20 text-emerald-400' :
                                            health >= 70 ? 'bg-amber-500/20 text-amber-400' :
                                            'bg-red-500/20 text-red-400'
                                          }`}>
                                            Health: {health.toFixed(1)}%
                                          </span>
                                          {avgGrowth > 0 && (
                                            <span className={`flex items-center gap-1 ${avgGrowth > 3 ? 'text-red-400' : 'text-slate-400'}`}>
                                              <TrendingUp className="w-3 h-3" />
                                              {avgGrowth.toFixed(1)}%/wk
                                            </span>
                                          )}
                                          {criticalCount > 0 && (
                                            <span className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded">
                                              {criticalCount} critical
                                            </span>
                                          )}
                                        </div>
                                      </div>
                                      <div className="px-4 py-3 space-y-2">
                                        {issues.slice(0, 5).map((issue, idx) => {
                                          const isCritical = issue.toLowerCase().includes('critical');
                                          const isHigh = issue.toLowerCase().includes('high');
                                          return (
                                            <div key={idx} className="flex items-start gap-2 text-sm">
                                              <AlertTriangle className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                                                isCritical ? 'text-red-400' : isHigh ? 'text-amber-400' : 'text-slate-500'
                                              }`} />
                                              <span className="text-slate-300">{issue}</span>
                                            </div>
                                          );
                                        })}
                                        {issues.length > 5 && (
                                          <div className="text-xs text-slate-500 pl-6">
                                            +{issues.length - 5} more issues
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            );
                          })()}
                        </div>
                      ) : (
                        <p className="text-slate-300 leading-relaxed">{agenticExecution.result.analysis_summary}</p>
                      )}
                    </div>
                  )}

                  <div className="px-8 py-6">
                    {/* Key Metrics */}
                    <div className="grid grid-cols-4 gap-4 mb-8">
                      <div className="bg-slate-900/50 border border-slate-700/50 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-white">{(agenticExecution.result.trend_direction || 'Stable').charAt(0).toUpperCase() + (agenticExecution.result.trend_direction || 'stable').slice(1)}</div>
                        <div className="text-xs text-slate-500 uppercase tracking-wider mt-1">Capacity Trend</div>
                      </div>
                      <div className="bg-slate-900/50 border border-slate-700/50 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-cyan-400">{agenticExecution.result.growth_rate_percent_per_month?.toFixed(1) || 0}%</div>
                        <div className="text-xs text-slate-500 uppercase tracking-wider mt-1">Monthly Growth</div>
                      </div>
                      <div className="bg-slate-900/50 border border-slate-700/50 rounded-lg p-4 text-center">
                        <div className={`text-2xl font-bold ${(agenticExecution.result.current_node_utilization || 0) >= 80 ? 'text-amber-400' : 'text-white'}`}>
                          {agenticExecution.result.current_node_utilization?.toFixed(1) || 0}%
                        </div>
                        <div className="text-xs text-slate-500 uppercase tracking-wider mt-1">Node Utilization</div>
                      </div>
                      <div className="bg-slate-900/50 border border-slate-700/50 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-white">{agenticExecution.result.total_throughput_gbps?.toFixed(1) || 0}</div>
                        <div className="text-xs text-slate-500 uppercase tracking-wider mt-1">Throughput (Gbps)</div>
                      </div>
                    </div>

                    {/* Capacity Forecast */}
                    {agenticExecution.result.forecasts && agenticExecution.result.forecasts.length > 0 && (
                      <div className="mb-8">
                        <h3 className="text-base font-bold text-white border-b border-slate-600 pb-2 mb-4">Capacity Forecast</h3>
                        <table className="w-full">
                          <thead>
                            <tr className="bg-slate-900/50">
                              <th className="text-left py-3 px-4 font-semibold text-slate-400 text-sm">Forecast Period</th>
                              <th className="text-left py-3 px-4 font-semibold text-slate-400 text-sm">Node Utilization</th>
                              <th className="text-left py-3 px-4 font-semibold text-slate-400 text-sm">Bandwidth Usage</th>
                              <th className="text-left py-3 px-4 font-semibold text-slate-400 text-sm">Risk Level</th>
                              <th className="text-left py-3 px-4 font-semibold text-slate-400 text-sm">Confidence</th>
                            </tr>
                          </thead>
                          <tbody>
                            {agenticExecution.result.forecasts.map((forecast, idx) => (
                              <tr key={forecast.period_days} className={idx % 2 === 0 ? 'bg-slate-800/30' : 'bg-slate-900/30'}>
                                <td className="py-3 px-4 text-slate-300">{forecast.period_days} Days</td>
                                <td className="py-3 px-4 text-slate-300">{forecast.projected_node_utilization?.toFixed(1)}%</td>
                                <td className="py-3 px-4 text-slate-300">{forecast.projected_bandwidth_usage_gbps?.toFixed(2)} Gbps</td>
                                <td className="py-3 px-4">
                                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                    forecast.risk_level === 'critical' ? 'bg-red-500/20 text-red-400' :
                                    forecast.risk_level === 'high' ? 'bg-orange-500/20 text-orange-400' :
                                    forecast.risk_level === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                                    'bg-green-500/20 text-green-400'
                                  }`}>
                                    {forecast.risk_level.charAt(0).toUpperCase() + forecast.risk_level.slice(1)}
                                  </span>
                                </td>
                                <td className="py-3 px-4 text-slate-300">{((forecast.confidence || 0) * 100).toFixed(0)}%</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Per-Datacenter Capacity Forecasts */}
                    {agenticExecution.result.datacenter_forecasts && agenticExecution.result.datacenter_forecasts.length > 0 && (
                      <div className="mb-8">
                        <h3 className="text-base font-bold text-white border-b border-slate-600 pb-2 mb-4 flex items-center gap-2">
                          <Server className="w-4 h-4 text-cyan-400" />
                          Per-Datacenter Capacity Forecast ({agenticExecution.result.datacenter_forecasts.length} locations)
                        </h3>
                        <div className="space-y-4">
                          {agenticExecution.result.datacenter_forecasts.map((dcForecast) => (
                            <div key={dcForecast.dc_id} className="bg-slate-900/50 border border-slate-700/50 rounded-lg overflow-hidden">
                              {/* DC Header */}
                              <div className="px-4 py-3 bg-slate-800/50 flex items-center justify-between">
                                <div>
                                  <h4 className="font-semibold text-white">{dcForecast.dc_name}</h4>
                                  <p className="text-xs text-slate-400">{dcForecast.city} &bull; {dcForecast.dc_id}</p>
                                </div>
                                <div className="flex items-center gap-4 text-sm">
                                  <div className="text-center">
                                    <div className={`text-lg font-bold ${dcForecast.health_score >= 90 ? 'text-emerald-400' : dcForecast.health_score >= 70 ? 'text-amber-400' : 'text-red-400'}`}>
                                      {dcForecast.health_score?.toFixed(0) || 0}%
                                    </div>
                                    <div className="text-xs text-slate-500">Health</div>
                                  </div>
                                  <div className="text-center">
                                    <div className="text-lg font-bold text-cyan-400">{dcForecast.growth_rate_per_month?.toFixed(1) || 0}%</div>
                                    <div className="text-xs text-slate-500">Growth/mo</div>
                                  </div>
                                </div>
                              </div>
                              {/* Current State + Forecast Table */}
                              <div className="p-4">
                                <div className="grid grid-cols-2 gap-4 mb-3">
                                  <div className="bg-slate-800/50 rounded p-3">
                                    <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Current Power</div>
                                    <div className="text-xl font-bold text-white">{dcForecast.current_power_util?.toFixed(1) || 0}%</div>
                                    <div className="mt-1.5 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                                      <div className={`h-full rounded-full ${dcForecast.current_power_util >= 90 ? 'bg-red-500' : dcForecast.current_power_util >= 70 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                                        style={{ width: `${Math.min(100, dcForecast.current_power_util || 0)}%` }} />
                                    </div>
                                  </div>
                                  <div className="bg-slate-800/50 rounded p-3">
                                    <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Current Rack Space</div>
                                    <div className="text-xl font-bold text-white">{dcForecast.current_rack_util?.toFixed(1) || 0}%</div>
                                    <div className="mt-1.5 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                                      <div className={`h-full rounded-full ${dcForecast.current_rack_util >= 90 ? 'bg-red-500' : dcForecast.current_rack_util >= 70 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                                        style={{ width: `${Math.min(100, dcForecast.current_rack_util || 0)}%` }} />
                                    </div>
                                  </div>
                                </div>
                                <table className="w-full text-sm">
                                  <thead>
                                    <tr className="bg-slate-800/30">
                                      <th className="text-left py-2 px-3 font-semibold text-slate-400 text-xs">Period</th>
                                      <th className="text-left py-2 px-3 font-semibold text-slate-400 text-xs">Power Util</th>
                                      <th className="text-left py-2 px-3 font-semibold text-slate-400 text-xs">Rack Util</th>
                                      <th className="text-left py-2 px-3 font-semibold text-slate-400 text-xs">Risk</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {dcForecast.forecasts.map((f, idx) => (
                                      <tr key={f.period_days} className={idx % 2 === 0 ? 'bg-slate-800/20' : ''}>
                                        <td className="py-2 px-3 text-slate-300">{f.period_days === 365 ? '1 Year' : `${f.period_days} Days`}</td>
                                        <td className={`py-2 px-3 ${f.projected_power_util >= 90 ? 'text-red-400 font-semibold' : f.projected_power_util >= 75 ? 'text-amber-400' : 'text-slate-300'}`}>
                                          {f.projected_power_util?.toFixed(1)}%
                                        </td>
                                        <td className={`py-2 px-3 ${f.projected_rack_util >= 90 ? 'text-red-400 font-semibold' : f.projected_rack_util >= 75 ? 'text-amber-400' : 'text-slate-300'}`}>
                                          {f.projected_rack_util?.toFixed(1)}%
                                        </td>
                                        <td className="py-2 px-3">
                                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                                            f.risk_level === 'critical' ? 'bg-red-500/20 text-red-400' :
                                            f.risk_level === 'high' ? 'bg-orange-500/20 text-orange-400' :
                                            f.risk_level === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                                            'bg-green-500/20 text-green-400'
                                          }`}>
                                            {f.risk_level.charAt(0).toUpperCase() + f.risk_level.slice(1)}
                                          </span>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Two Column Layout for Upgrade & Hardware */}
                    <div className="grid grid-cols-2 gap-8 mb-8">
                      {/* Upgrade Analysis */}
                      {agenticExecution.upgrade_analysis && (
                        <div>
                          <h3 className="text-base font-bold text-white border-b border-slate-600 pb-2 mb-4">Upgrade Impact Analysis</h3>
                          <table className="w-full text-sm">
                            <tbody>
                              <tr className="border-b border-slate-700/50">
                                <td className="py-2 text-slate-400">Nodes Analyzed</td>
                                <td className="py-2 text-right font-semibold text-white">{agenticExecution.upgrade_analysis.nodes_analyzed.toLocaleString()}</td>
                              </tr>
                              <tr className="border-b border-slate-700/50">
                                <td className="py-2 text-slate-400">Target Connection</td>
                                <td className="py-2 text-right font-semibold text-cyan-400">{agenticExecution.upgrade_analysis.upgrade_target}</td>
                              </tr>
                              <tr className="border-b border-slate-700/50">
                                <td className="py-2 text-slate-400">Users Benefiting</td>
                                <td className="py-2 text-right font-semibold text-white">{agenticExecution.upgrade_analysis.users_to_benefit.toLocaleString()}</td>
                              </tr>
                              <tr className="border-b border-slate-700/50">
                                <td className="py-2 text-slate-400">Bandwidth Improvement</td>
                                <td className="py-2 text-right font-semibold text-emerald-400">+{agenticExecution.upgrade_analysis.bandwidth_improvement_percent.toFixed(1)}%</td>
                              </tr>
                              <tr className="border-b border-slate-700/50">
                                <td className="py-2 text-slate-400">Latency Reduction</td>
                                <td className="py-2 text-right font-semibold text-emerald-400">-{agenticExecution.upgrade_analysis.latency_improvement_percent.toFixed(1)}%</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* Hardware Compatibility */}
                      {agenticExecution.hardware_compatibility && (
                        <div>
                          <h3 className="text-base font-bold text-white border-b border-slate-600 pb-2 mb-4">Hardware Assessment</h3>
                          <table className="w-full text-sm">
                            <tbody>
                              <tr className="border-b border-slate-700/50">
                                <td className="py-2 text-slate-400">Compatible Equipment</td>
                                <td className="py-2 text-right font-semibold text-emerald-400">{agenticExecution.hardware_compatibility.compatible_count}</td>
                              </tr>
                              <tr className="border-b border-slate-700/50">
                                <td className="py-2 text-slate-400">Partial Upgrade Required</td>
                                <td className="py-2 text-right font-semibold text-amber-400">{agenticExecution.hardware_compatibility.partial_upgrade_count}</td>
                              </tr>
                              <tr className="border-b border-slate-700/50">
                                <td className="py-2 text-slate-400">Full Replacement</td>
                                <td className="py-2 text-right font-semibold text-red-400">{agenticExecution.hardware_compatibility.replacement_count}</td>
                              </tr>
                              <tr className="border-b border-slate-700/50">
                                <td className="py-2 text-slate-400">Implementation Timeline</td>
                                <td className="py-2 text-right font-semibold text-white">{agenticExecution.hardware_compatibility.installation_timeline_days} days</td>
                              </tr>
                              <tr>
                                <td className="py-2 text-slate-400">Estimated Total Cost</td>
                                <td className="py-2 text-right font-bold text-lg text-white">${agenticExecution.hardware_compatibility.estimated_total_cost.toLocaleString()}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>

                    {/* Datacenter Analysis */}
                    {agenticExecution.datacenter_analysis && (
                      <div className="mb-8">
                        <h3 className="text-base font-bold text-white border-b border-slate-600 pb-2 mb-4">Datacenter Infrastructure</h3>
                        <table className="w-full mb-4">
                          <thead>
                            <tr className="bg-slate-900/50">
                              <th className="text-left py-2 px-4 font-semibold text-slate-400 text-sm">Metric</th>
                              <th className="text-left py-2 px-4 font-semibold text-slate-400 text-sm">Value</th>
                              <th className="text-left py-2 px-4 font-semibold text-slate-400 text-sm">Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr className="border-b border-slate-700/50">
                              <td className="py-2 px-4 text-slate-400">Total Components</td>
                              <td className="py-2 px-4 font-semibold text-white">{agenticExecution.datacenter_analysis.total_components}</td>
                              <td className="py-2 px-4 text-slate-500">—</td>
                            </tr>
                            <tr className="border-b border-slate-700/50 bg-slate-900/30">
                              <td className="py-2 px-4 text-slate-400">Health Score</td>
                              <td className="py-2 px-4 font-semibold text-white">{agenticExecution.datacenter_analysis.overall_health_score?.toFixed(1) || 0}%</td>
                              <td className="py-2 px-4">
                                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                  (agenticExecution.datacenter_analysis.overall_health_score || 0) >= 90 ? 'bg-emerald-500/20 text-emerald-400' :
                                  (agenticExecution.datacenter_analysis.overall_health_score || 0) >= 70 ? 'bg-amber-500/20 text-amber-400' :
                                  'bg-red-500/20 text-red-400'
                                }`}>
                                  {(agenticExecution.datacenter_analysis.overall_health_score || 0) >= 90 ? 'Healthy' :
                                   (agenticExecution.datacenter_analysis.overall_health_score || 0) >= 70 ? 'Degraded' : 'Critical'}
                                </span>
                              </td>
                            </tr>
                            <tr className="border-b border-slate-700/50">
                              <td className="py-2 px-4 text-slate-400">Critical Issues</td>
                              <td className="py-2 px-4 font-semibold text-white">
                                {Array.isArray(agenticExecution.datacenter_analysis.critical_issues)
                                  ? agenticExecution.datacenter_analysis.critical_issues.length
                                  : (agenticExecution.datacenter_analysis.critical_issues || 0)}
                              </td>
                              <td className="py-2 px-4">
                                {(Array.isArray(agenticExecution.datacenter_analysis.critical_issues)
                                  ? agenticExecution.datacenter_analysis.critical_issues.length > 0
                                  : (agenticExecution.datacenter_analysis.critical_issues || 0) > 0) ? (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-500/20 text-red-400">
                                    Attention Required
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/20 text-emerald-400">
                                    No Issues
                                  </span>
                                )}
                              </td>
                            </tr>
                            <tr className="bg-slate-900/30">
                              <td className="py-2 px-4 text-slate-400">Estimated Upgrade Cost</td>
                              <td className="py-2 px-4 font-semibold text-white">${((agenticExecution.datacenter_analysis.estimated_total_upgrade_cost || 0) / 1000000).toFixed(2)}M</td>
                              <td className="py-2 px-4 text-slate-500">—</td>
                            </tr>
                          </tbody>
                        </table>
                        {/* Critical Issues List */}
                        {Array.isArray(agenticExecution.datacenter_analysis.critical_issues) &&
                         agenticExecution.datacenter_analysis.critical_issues.length > 0 && (
                          <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-4 mb-4">
                            <h4 className="font-semibold text-red-400 text-sm mb-3 flex items-center gap-2">
                              <AlertTriangle className="w-4 h-4" />
                              Critical Issues ({agenticExecution.datacenter_analysis.critical_issues.length})
                            </h4>
                            <ul className="space-y-2">
                              {agenticExecution.datacenter_analysis.critical_issues.slice(0, 10).map((issue, idx) => (
                                <li key={idx} className="flex items-start gap-2 text-sm">
                                  <span className="text-red-400 mt-1">•</span>
                                  <span className="text-slate-300">{issue}</span>
                                </li>
                              ))}
                              {agenticExecution.datacenter_analysis.critical_issues.length > 10 && (
                                <li className="text-xs text-slate-500 pl-4">
                                  +{agenticExecution.datacenter_analysis.critical_issues.length - 10} more issues
                                </li>
                              )}
                            </ul>
                          </div>
                        )}

                        {agenticExecution.datacenter_analysis.upgrade_recommendations && agenticExecution.datacenter_analysis.upgrade_recommendations.length > 0 && (
                          <div className="bg-slate-900/30 border border-slate-700/50 rounded-lg p-4">
                            <h4 className="font-semibold text-slate-300 text-sm mb-2">Infrastructure Upgrade Recommendations</h4>
                            <div className="space-y-2 text-sm">
                              {agenticExecution.datacenter_analysis.upgrade_recommendations.slice(0, 5).map((rec, idx) => (
                                <div key={idx} className="flex items-start gap-2 p-2 bg-slate-800/30 rounded">
                                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                                    rec.priority === 'critical' ? 'bg-red-500/20 text-red-400' :
                                    rec.priority === 'high' ? 'bg-orange-500/20 text-orange-400' :
                                    'bg-yellow-500/20 text-yellow-400'
                                  }`}>
                                    {rec.priority.toUpperCase()}
                                  </span>
                                  <div className="flex-1">
                                    <span className="text-slate-300">{rec.component_type} {rec.name}</span>
                                    <p className="text-slate-500 text-xs mt-0.5">{rec.recommendation}</p>
                                  </div>
                                  <span className="text-slate-400">${(rec.estimated_cost / 1000).toFixed(0)}K</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Regional Breakdown */}
                        {agenticExecution.datacenter_analysis.components_by_location &&
                         Object.keys(agenticExecution.datacenter_analysis.components_by_location).length > 0 && (
                          <div className="mt-6">
                            <h4 className="font-semibold text-white text-sm mb-3 flex items-center gap-2">
                              <Globe className="w-4 h-4 text-cyan-400" />
                              Regional Breakdown
                            </h4>
                            <table className="w-full mb-4">
                              <thead>
                                <tr className="bg-slate-900/50">
                                  <th className="text-left py-2 px-4 font-semibold text-slate-400 text-sm">Location</th>
                                  <th className="text-left py-2 px-4 font-semibold text-slate-400 text-sm">Components</th>
                                  <th className="text-left py-2 px-4 font-semibold text-slate-400 text-sm">Health</th>
                                  <th className="text-left py-2 px-4 font-semibold text-slate-400 text-sm">Growth/Week</th>
                                  <th className="text-left py-2 px-4 font-semibold text-slate-400 text-sm">Critical</th>
                                </tr>
                              </thead>
                              <tbody>
                                {Object.entries(agenticExecution.datacenter_analysis.components_by_location)
                                  .sort(([, a], [, b]) => (b as number) - (a as number))
                                  .map(([location, count], idx) => {
                                    const health = agenticExecution.datacenter_analysis?.health_by_location?.[location] || 0;
                                    const growth = agenticExecution.datacenter_analysis?.growth_by_location?.[location];
                                    const criticalCount = growth?.critical_count || 0;
                                    const avgGrowth = growth?.avg_growth_per_week || 0;
                                    return (
                                      <tr key={location} className={idx % 2 === 0 ? 'bg-slate-800/30' : 'bg-slate-900/30'}>
                                        <td className="py-2 px-4 text-slate-300 font-medium">{location}</td>
                                        <td className="py-2 px-4 text-white">{count as number}</td>
                                        <td className="py-2 px-4">
                                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                            health >= 90 ? 'bg-emerald-500/20 text-emerald-400' :
                                            health >= 70 ? 'bg-amber-500/20 text-amber-400' :
                                            'bg-red-500/20 text-red-400'
                                          }`}>
                                            {health.toFixed(1)}%
                                          </span>
                                        </td>
                                        <td className="py-2 px-4">
                                          <span className={`inline-flex items-center gap-1 text-sm ${
                                            avgGrowth > 3 ? 'text-red-400' : avgGrowth > 1 ? 'text-amber-400' : 'text-slate-400'
                                          }`}>
                                            {avgGrowth > 0 && <TrendingUp className="w-3 h-3" />}
                                            {avgGrowth.toFixed(1)}%
                                          </span>
                                        </td>
                                        <td className="py-2 px-4">
                                          {criticalCount > 0 ? (
                                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-500/20 text-red-400">
                                              {criticalCount}
                                            </span>
                                          ) : (
                                            <span className="text-slate-500">—</span>
                                          )}
                                        </td>
                                      </tr>
                                    );
                                  })}
                              </tbody>
                            </table>

                            {/* Issues by Location */}
                            {agenticExecution.datacenter_analysis.issues_by_location &&
                             Object.values(agenticExecution.datacenter_analysis.issues_by_location).some(issues => (issues as string[]).length > 0) && (
                              <div className="mt-4">
                                <h5 className="font-medium text-slate-400 text-xs uppercase tracking-wide mb-2">Issues by Location</h5>
                                <div className="space-y-3">
                                  {Object.entries(agenticExecution.datacenter_analysis.issues_by_location)
                                    .filter(([, issues]) => (issues as string[]).length > 0)
                                    .sort(([, a], [, b]) => (b as string[]).length - (a as string[]).length)
                                    .slice(0, 5)
                                    .map(([location, issues]) => (
                                      <div key={location} className="bg-slate-900/40 border border-slate-700/30 rounded p-3">
                                        <div className="flex items-center justify-between mb-2">
                                          <span className="font-medium text-slate-300 text-sm">{location}</span>
                                          <span className="text-xs text-red-400">{(issues as string[]).length} issue(s)</span>
                                        </div>
                                        <ul className="space-y-1">
                                          {(issues as string[]).slice(0, 3).map((issue, idx) => (
                                            <li key={idx} className="text-xs text-slate-400 flex items-start gap-2">
                                              <AlertTriangle className="w-3 h-3 text-amber-500 mt-0.5 flex-shrink-0" />
                                              {issue}
                                            </li>
                                          ))}
                                          {(issues as string[]).length > 3 && (
                                            <li className="text-xs text-slate-500">
                                              +{(issues as string[]).length - 3} more issues
                                            </li>
                                          )}
                                        </ul>
                                      </div>
                                    ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Detailed Sites Analysis */}
                    {agenticExecution.datacenter_analysis?.sites && agenticExecution.datacenter_analysis.sites.length > 0 && (
                      <div className="mb-8">
                        <h3 className="text-base font-bold text-white border-b border-slate-600 pb-2 mb-4 flex items-center gap-2">
                          <Server className="w-4 h-4 text-cyan-400" />
                          Sites Detail ({agenticExecution.datacenter_analysis.sites.length} sites in region)
                        </h3>
                        <div className="space-y-4">
                          {agenticExecution.datacenter_analysis.sites.map((site) => (
                            <div key={site.dc_id} className="bg-slate-900/50 border border-slate-700/50 rounded-lg overflow-hidden">
                              {/* Site Header */}
                              <div className={`px-4 py-3 flex items-center justify-between ${
                                site.critical_count > 0 ? 'bg-red-500/10 border-l-4 border-red-500' :
                                site.health_score < 70 ? 'bg-amber-500/10 border-l-4 border-amber-500' :
                                'bg-slate-800/50'
                              }`}>
                                <div>
                                  <h4 className="font-semibold text-white">{site.name}</h4>
                                  <p className="text-xs text-slate-400">{site.city} • {site.dc_id}</p>
                                </div>
                                <div className="flex items-center gap-4">
                                  <div className="text-center">
                                    <div className={`text-lg font-bold ${
                                      site.health_score >= 90 ? 'text-emerald-400' :
                                      site.health_score >= 70 ? 'text-amber-400' : 'text-red-400'
                                    }`}>
                                      {site.health_score}%
                                    </div>
                                    <div className="text-xs text-slate-500">Health</div>
                                  </div>
                                  <div className="text-center">
                                    <div className="text-lg font-bold text-white">{site.total_components}</div>
                                    <div className="text-xs text-slate-500">Components</div>
                                  </div>
                                  {site.critical_count > 0 && (
                                    <div className="text-center">
                                      <div className="text-lg font-bold text-red-400">{site.critical_count}</div>
                                      <div className="text-xs text-slate-500">Critical</div>
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Site Details Grid */}
                              <div className="p-4">
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                                  {/* Component Breakdown */}
                                  <div className="bg-slate-800/50 rounded p-3">
                                    <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Components</div>
                                    <div className="space-y-1">
                                      {Object.entries(site.components_by_type || {}).map(([type, count]) => (
                                        <div key={type} className="flex justify-between text-sm">
                                          <span className="text-slate-400">{type}</span>
                                          <span className="text-white font-medium">{count}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>

                                  {/* Power Utilization */}
                                  <div className="bg-slate-800/50 rounded p-3">
                                    <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Power</div>
                                    <div className="text-2xl font-bold text-white mb-1">
                                      {site.power_utilization_percent?.toFixed(1) || 0}%
                                    </div>
                                    <div className="text-xs text-slate-400">
                                      {site.current_power_mw?.toFixed(1) || 0} / {site.power_capacity_mw?.toFixed(1) || 0} MW
                                    </div>
                                    <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                                      <div
                                        className={`h-full rounded-full ${
                                          site.power_utilization_percent >= 90 ? 'bg-red-500' :
                                          site.power_utilization_percent >= 70 ? 'bg-amber-500' : 'bg-emerald-500'
                                        }`}
                                        style={{ width: `${Math.min(100, site.power_utilization_percent || 0)}%` }}
                                      />
                                    </div>
                                  </div>

                                  {/* Rack Utilization */}
                                  <div className="bg-slate-800/50 rounded p-3">
                                    <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Rack Space</div>
                                    <div className="text-2xl font-bold text-white mb-1">
                                      {site.rack_utilization_percent?.toFixed(1) || 0}%
                                    </div>
                                    <div className="text-xs text-slate-400">
                                      {site.used_rack_units || 0} / {site.total_rack_units || 0} RU
                                    </div>
                                    <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                                      <div
                                        className={`h-full rounded-full ${
                                          site.rack_utilization_percent >= 90 ? 'bg-red-500' :
                                          site.rack_utilization_percent >= 70 ? 'bg-amber-500' : 'bg-emerald-500'
                                        }`}
                                        style={{ width: `${Math.min(100, site.rack_utilization_percent || 0)}%` }}
                                      />
                                    </div>
                                  </div>

                                  {/* Growth */}
                                  <div className="bg-slate-800/50 rounded p-3">
                                    <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Growth Trend</div>
                                    <div className={`text-2xl font-bold flex items-center gap-2 ${
                                      site.avg_growth_per_week > 3 ? 'text-red-400' :
                                      site.avg_growth_per_week > 1 ? 'text-amber-400' : 'text-slate-300'
                                    }`}>
                                      {site.avg_growth_per_week > 0 && <TrendingUp className="w-5 h-5" />}
                                      {site.avg_growth_per_week?.toFixed(1) || 0}%
                                    </div>
                                    <div className="text-xs text-slate-400">per week</div>
                                  </div>
                                </div>

                                {/* Site Issues */}
                                {site.issues && site.issues.length > 0 && (
                                  <div className="mb-4">
                                    <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Issues ({site.issues.length})</div>
                                    <div className="space-y-1">
                                      {site.issues.slice(0, 5).map((issue, i) => (
                                        <div key={i} className="flex items-start gap-2 text-sm">
                                          <AlertTriangle className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                                            issue.toLowerCase().includes('critical') ? 'text-red-400' : 'text-amber-500'
                                          }`} />
                                          <span className="text-slate-300">{issue}</span>
                                        </div>
                                      ))}
                                      {site.issues.length > 5 && (
                                        <div className="text-xs text-slate-500 pl-6">+{site.issues.length - 5} more issues</div>
                                      )}
                                    </div>
                                  </div>
                                )}

                                {/* Site Recommendations */}
                                {site.recommendations && site.recommendations.length > 0 && (
                                  <div className="bg-cyan-500/5 border border-cyan-500/20 rounded p-3">
                                    <div className="text-xs text-cyan-400 uppercase tracking-wide mb-2">Recommendations</div>
                                    <ul className="space-y-1">
                                      {site.recommendations.map((rec, i) => (
                                        <li key={i} className="flex items-start gap-2 text-sm">
                                          <ArrowRight className="w-4 h-4 mt-0.5 flex-shrink-0 text-cyan-500" />
                                          <span className="text-slate-300">{rec}</span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Bandwidth Bottlenecks */}
                    {agenticExecution.result.bandwidth_bottlenecks && agenticExecution.result.bandwidth_bottlenecks.length > 0 && (
                      <div className="mb-8">
                        <h3 className="text-base font-bold text-white border-b border-red-500/50 pb-2 mb-4 flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-red-400" />
                          Bandwidth Bottlenecks
                        </h3>
                        <div className="bg-red-500/5 border border-red-500/20 rounded-lg overflow-hidden">
                          <table className="w-full">
                            <thead>
                              <tr className="bg-red-500/10">
                                <th className="text-left py-2 px-4 font-semibold text-red-400 text-sm">Location</th>
                                <th className="text-left py-2 px-4 font-semibold text-red-400 text-sm">Utilization</th>
                                <th className="text-left py-2 px-4 font-semibold text-red-400 text-sm">Status</th>
                                <th className="text-left py-2 px-4 font-semibold text-red-400 text-sm">Time to Breach</th>
                              </tr>
                            </thead>
                            <tbody>
                              {agenticExecution.result.bandwidth_bottlenecks.map((bottleneck, idx) => (
                                <tr key={idx} className="border-t border-red-500/20">
                                  <td className="py-2 px-4 text-slate-300 font-medium">{bottleneck.location}</td>
                                  <td className={`py-2 px-4 font-semibold ${bottleneck.current_utilization >= 90 ? 'text-red-400' : 'text-amber-400'}`}>
                                    {bottleneck.current_utilization?.toFixed(1)}%
                                  </td>
                                  <td className="py-2 px-4">
                                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                      bottleneck.current_utilization >= 90 ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
                                    }`}>
                                      {bottleneck.current_utilization >= 90 ? 'Critical' : 'Warning'}
                                    </span>
                                  </td>
                                  <td className="py-2 px-4 text-slate-400">
                                    {bottleneck.projected_breach_days ? `${bottleneck.projected_breach_days} days` : '—'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Capacity Constraints */}
                    {agenticExecution.result.capacity_constraints && agenticExecution.result.capacity_constraints.length > 0 && (
                      <div className="mb-8">
                        <h3 className="text-base font-bold text-white border-b border-amber-500/50 pb-2 mb-4">Capacity Constraints</h3>
                        <table className="w-full">
                          <thead>
                            <tr className="bg-slate-900/50">
                              <th className="text-left py-2 px-4 font-semibold text-slate-400 text-sm">Resource</th>
                              <th className="text-left py-2 px-4 font-semibold text-slate-400 text-sm">Severity</th>
                              <th className="text-left py-2 px-4 font-semibold text-slate-400 text-sm">Affected Components</th>
                            </tr>
                          </thead>
                          <tbody>
                            {agenticExecution.result.capacity_constraints.map((constraint, idx) => (
                              <tr key={idx} className={idx % 2 === 0 ? 'bg-slate-800/30' : 'bg-slate-900/30'}>
                                <td className="py-2 px-4 text-slate-300 font-medium capitalize">{constraint.resource}</td>
                                <td className="py-2 px-4">
                                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                    constraint.severity === 'high' ? 'bg-red-500/20 text-red-400' :
                                    constraint.severity === 'medium' ? 'bg-amber-500/20 text-amber-400' :
                                    'bg-emerald-500/20 text-emerald-400'
                                  }`}>
                                    {constraint.severity.charAt(0).toUpperCase() + constraint.severity.slice(1)}
                                  </span>
                                </td>
                                <td className="py-2 px-4 text-slate-400 text-sm">{constraint.affected_components?.join(', ') || '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Strategic Recommendations */}
                    {agenticExecution.result.recommendations && agenticExecution.result.recommendations.length > 0 && (
                      <div className="mb-8">
                        <h3 className="text-base font-bold text-white border-b border-cyan-500/50 pb-2 mb-4">Strategic Recommendations</h3>
                        <div className="space-y-3">
                          {agenticExecution.result.recommendations.map((rec, idx) => (
                            <div key={idx} className="flex gap-4 items-start">
                              <span className="flex-shrink-0 w-7 h-7 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center font-bold text-sm">
                                {idx + 1}
                              </span>
                              <p className="text-slate-300 leading-relaxed pt-0.5">{rec}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Report Footer */}
                  <div className="bg-slate-900/50 px-8 py-4 border-t border-slate-700/50">
                    <div className="flex justify-between items-center text-xs text-slate-500">
                      <span>Generated by AI-Powered Capacity Planning System</span>
                      <span>Confidential — For Internal Use Only</span>
                    </div>
                  </div>
                </div>
              )}

              {agenticExecution.status === 'failed' && agenticExecution.error && (
                <Card className="p-5 bg-red-500/5 border-red-500/30">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-6 h-6 text-red-400 flex-shrink-0" />
                    <div>
                      <h4 className="text-red-400 font-semibold">Analysis Failed</h4>
                      <p className="text-slate-400 text-sm mt-1">{agenticExecution.error}</p>
                    </div>
                  </div>
                </Card>
              )}
            </div>
          )}

          {/* Current Result Summary */}
          {currentResult && !agenticExecution && (
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-slate-400" />
                  <span className="text-sm font-medium text-slate-300">Latest Simulation</span>
                </div>
                <span className="text-xs text-slate-500">{new Date(currentResult.created_at).toLocaleString()}</span>
              </div>
              <div className="grid grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-slate-500 text-xs">Projected Loss</div>
                  <div className="text-red-400 font-semibold">{formatCurrency(currentResult.projected_revenue_loss)}</div>
                </div>
                <div>
                  <div className="text-slate-500 text-xs">SLA Risk</div>
                  <div className="text-amber-400 font-semibold">{currentResult.risk_score.toFixed(0)}%</div>
                </div>
                <div>
                  <div className="text-slate-500 text-xs">Nodes Affected</div>
                  <div className="text-white font-semibold">{currentResult.affected_node_count}</div>
                </div>
                <div>
                  <div className="text-slate-500 text-xs">Capacity Used</div>
                  <div className="text-white font-semibold">{(currentResult.simulated_metrics.capacity_utilization || 0).toFixed(0)}%</div>
                </div>
              </div>
            </div>
          )}

          {/* Simulation History */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-700/50 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <History className="w-4 h-4 text-slate-400" />
                <span className="text-sm font-medium text-slate-300">Simulation History</span>
                <span className="text-xs text-slate-500">{results.length} records</span>
              </div>
              <div className="flex items-center gap-2">
                {results.length > 0 && (
                  <>
                    <button
                      onClick={toggleSelectAll}
                      className="flex items-center gap-1.5 px-2 py-1 text-xs text-slate-400 hover:text-slate-200 rounded hover:bg-slate-700/50 transition-colors"
                      title={selectedResultIds.size === results.length ? 'Deselect All' : 'Select All'}
                    >
                      {selectedResultIds.size === results.length ? (
                        <CheckSquare className="w-3.5 h-3.5" />
                      ) : (
                        <Square className="w-3.5 h-3.5" />
                      )}
                      <span>{selectedResultIds.size === results.length ? 'Deselect' : 'Select All'}</span>
                    </button>
                    {selectedResultIds.size > 0 && (
                      <button
                        onClick={handleDeleteSelected}
                        disabled={isDeleting}
                        className="flex items-center gap-1.5 px-2 py-1 text-xs text-red-400 hover:text-red-300 rounded hover:bg-red-500/10 transition-colors disabled:opacity-50"
                      >
                        {isDeleting ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="w-3.5 h-3.5" />
                        )}
                        <span>Delete ({selectedResultIds.size})</span>
                      </button>
                    )}
                  </>
                )}
                <button
                  onClick={loadHistory}
                  className="p-1.5 rounded-lg hover:bg-slate-700/50 transition-colors"
                >
                  <RefreshCw className={`w-4 h-4 text-slate-400 ${loadingHistory ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>

            {loadingHistory ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
              </div>
            ) : results.length === 0 ? (
              <div className="text-center py-8">
                <BarChart3 className="w-10 h-10 mx-auto mb-2 text-slate-600" />
                <p className="text-sm text-slate-400">No simulations yet</p>
              </div>
            ) : (
              <div className="max-h-[500px] overflow-y-auto custom-scrollbar">
                {results.map(result => (
                  <div key={result.result_id} className="flex items-start border-b border-slate-700/30 last:border-0">
                    {/* Selection checkbox */}
                    <div className="flex items-center p-3 pt-4">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleResultSelection(result.result_id);
                        }}
                        className="text-slate-400 hover:text-slate-200 transition-colors"
                      >
                        {selectedResultIds.has(result.result_id) ? (
                          <CheckSquare className="w-4 h-4 text-cyan-400" />
                        ) : (
                          <Square className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                    {/* Result card */}
                    <div className="flex-1">
                      <SimulationResultCard
                        result={result}
                        expanded={expandedResult === result.result_id}
                        onToggle={() => setExpandedResult(expandedResult === result.result_id ? null : result.result_id)}
                      />
                    </div>
                    {/* Delete button */}
                    <div className="flex items-center p-3 pt-4">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteResult(result.result_id);
                        }}
                        disabled={isDeleting}
                        className="text-slate-500 hover:text-red-400 transition-colors disabled:opacity-50"
                        title="Delete this result"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Custom scrollbar styles */}
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #334155;
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #475569;
        }
      `}</style>
    </div>
  );
});

DigitalTwinView.displayName = 'DigitalTwinView';

export default DigitalTwinView;
