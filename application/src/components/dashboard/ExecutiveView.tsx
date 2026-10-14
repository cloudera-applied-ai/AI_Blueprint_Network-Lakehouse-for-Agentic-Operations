import { memo, useState, useEffect, useCallback } from 'react';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  AlertTriangle,
  Zap,
  Globe,
  RefreshCw,
  Loader2,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  Clock,
  Database,
  FileText,
  CheckCircle,
  XCircle,
  Minus,
} from 'lucide-react';
import {
  getExecutiveSummary,
  getFinancialSummary,
  getSLAStatus,
  type ExecutiveSummary,
  type FinancialSummary,
  type SLAStatus,
} from '@/services/apiClient';

// Extended types for new historical data fields
interface KPITrendPoint {
  timestamp: string;
  ds_snr_db: number;
  packet_loss_percent: number;
  latency_ms: number;
  downstream_throughput_mbps: number;
  node_cpu_utilization?: number;
  node_memory_utilization?: number;
}

interface PeriodComparisonMetric {
  metric_name: string;
  current_value: number;
  previous_value: number;
  change_percent: number;
  trend: 'improving' | 'stable' | 'declining';
}

interface ExecutiveInsight {
  id: string;
  type: string;
  severity: string;
  title: string;
  description: string;
  recommendation: string;
}

// Extended ExecutiveSummary type
interface ExtendedExecutiveSummary extends ExecutiveSummary {
  period_hours?: number;
  historical_revenue_loss?: number;
  mttr_minutes?: number;
  kpi_trend_data?: KPITrendPoint[];
  period_comparison?: PeriodComparisonMetric[];
  ai_insights?: ExecutiveInsight[];
  data_source?: string;
}

const formatCurrency = (value: number): string => {
  if (value >= 1000000000) {
    return `$${(value / 1000000000).toFixed(2)}B`;
  } else if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(2)}M`;
  } else if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`;
  }
  return `$${value.toFixed(0)}`;
};

const formatPercent = (value: number): string => `${value.toFixed(2)}%`;

const formatMetricName = (name: string): string => {
  return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

// KPI Trend Chart Component
const KPITrendChart = memo(({ data }: { data: KPITrendPoint[] }) => {
  if (!data || data.length < 2) return <div className="text-gray-500 text-sm">No trend data available</div>;

  const latencyData = data.map(d => d.latency_ms);
  const throughputData = data.map(d => d.downstream_throughput_mbps);
  const snrData = data.map(d => d.ds_snr_db);

  const height = 100;

  const createPath = (values: number[], color: string) => {
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    const points = values.map((value, index) => {
      const x = (index / (values.length - 1)) * 100;
      const y = height - ((value - min) / range) * (height - 10);
      return `${x},${y}`;
    }).join(' ');

    return (
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="2"
        points={points}
        vectorEffect="non-scaling-stroke"
      />
    );
  };

  return (
    <div className="w-full">
      <div className="flex gap-4 mb-2 text-xs">
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-cyan-400 inline-block"></span> Latency</span>
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-green-400 inline-block"></span> Throughput</span>
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-purple-400 inline-block"></span> DS SNR</span>
      </div>
      <svg viewBox={`0 0 100 ${height}`} className="w-full h-24" preserveAspectRatio="none">
        {createPath(latencyData, '#22d3ee')}
        {createPath(throughputData, '#4ade80')}
        {createPath(snrData, '#c084fc')}
      </svg>
      <div className="flex justify-between text-xs text-gray-500 mt-1">
        <span>{new Date(data[0].timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        <span>{new Date(data[data.length - 1].timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
    </div>
  );
});

KPITrendChart.displayName = 'KPITrendChart';

// Status indicator component
const StatusIndicator = memo(({ status }: { status: 'good' | 'warning' | 'critical' }) => {
  const colors = {
    good: 'bg-green-500',
    warning: 'bg-yellow-500',
    critical: 'bg-red-500',
  };
  return <span className={`inline-block w-2 h-2 rounded-full ${colors[status]}`} />;
});

StatusIndicator.displayName = 'StatusIndicator';

// Trend icon component
const TrendIcon = memo(({ trend, size = 14 }: { trend: 'improving' | 'stable' | 'declining'; size?: number }) => {
  if (trend === 'improving') return <TrendingUp className="text-green-400" style={{ width: size, height: size }} />;
  if (trend === 'declining') return <TrendingDown className="text-red-400" style={{ width: size, height: size }} />;
  return <Minus className="text-gray-400" style={{ width: size, height: size }} />;
});

TrendIcon.displayName = 'TrendIcon';

const ExecutiveView = memo(() => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [executiveSummary, setExecutiveSummary] = useState<ExtendedExecutiveSummary | null>(null);
  const [financialSummary, setFinancialSummary] = useState<FinancialSummary | null>(null);
  const [slaStatus, setSlaStatus] = useState<SLAStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAllRegions, setShowAllRegions] = useState(false);
  const [showInsights, setShowInsights] = useState(true);

  const loadData = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const [execData, finData, slaData] = await Promise.all([
        getExecutiveSummary(24),
        getFinancialSummary(30),
        getSLAStatus(),
      ]);

      setExecutiveSummary(execData);
      setFinancialSummary(finData);
      setSlaStatus(slaData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load executive data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(() => loadData(true), 60000);
    return () => clearInterval(interval);
  }, [loadData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-800/50 rounded-lg">
        <div className="flex items-center gap-3 text-gray-400">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Loading executive report...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96 bg-red-900/20 rounded-lg border border-red-500/30">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={() => loadData()}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-white"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!executiveSummary || !financialSummary || !slaStatus) {
    return null;
  }

  const uptimeStatus = executiveSummary.network_uptime_percent >= 99.9 ? 'good' : executiveSummary.network_uptime_percent >= 99 ? 'warning' : 'critical';
  const slaStatusColor = slaStatus.status === 'healthy' ? 'good' : slaStatus.status === 'warning' ? 'warning' : 'critical';

  const displayedRegions = showAllRegions
    ? executiveSummary.regions
    : executiveSummary.regions.slice(0, 5);

  return (
    <div className="space-y-6 text-sm">
      {/* Report Header */}
      <div className="bg-gray-800/70 rounded-lg border border-gray-700 p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <FileText className="w-6 h-6 text-blue-400" />
            <div>
              <h1 className="text-xl font-bold text-white">Network Operations Executive Report</h1>
              <p className="text-gray-400 text-xs">
                Generated: {new Date(executiveSummary.timestamp).toLocaleString()} | Period: Last {executiveSummary.period_hours || 24} hours
              </p>
            </div>
          </div>
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 text-xs disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {/* Key Metrics Summary Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 bg-gray-900/50 rounded p-3">
          <div className="text-center border-r border-gray-700 last:border-r-0">
            <div className="text-lg font-bold text-white">{executiveSummary.total_nodes.toLocaleString()}</div>
            <div className="text-xs text-gray-400">Total Nodes</div>
          </div>
          <div className="text-center border-r border-gray-700 last:border-r-0">
            <div className="flex items-center justify-center gap-1">
              <StatusIndicator status={uptimeStatus} />
              <span className="text-lg font-bold text-white">{formatPercent(executiveSummary.network_uptime_percent)}</span>
            </div>
            <div className="text-xs text-gray-400">Network Uptime</div>
          </div>
          <div className="text-center border-r border-gray-700 last:border-r-0">
            <div className="flex items-center justify-center gap-1">
              <StatusIndicator status={slaStatusColor} />
              <span className="text-lg font-bold text-white">{formatPercent(executiveSummary.sla_compliance_percent)}</span>
            </div>
            <div className="text-xs text-gray-400">SLA Compliance</div>
          </div>
          <div className="text-center border-r border-gray-700 last:border-r-0">
            <div className="text-lg font-bold text-red-400">{formatCurrency(executiveSummary.historical_revenue_loss || financialSummary.actual_revenue_loss)}</div>
            <div className="text-xs text-gray-400">Revenue Impact</div>
          </div>
          <div className="text-center border-r border-gray-700 last:border-r-0">
            <div className="text-lg font-bold text-green-400">{formatCurrency(financialSummary.ai_savings)}</div>
            <div className="text-xs text-gray-400">AI Savings</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-cyan-400">{executiveSummary.mttr_minutes?.toFixed(1) || executiveSummary.avg_resolution_time_minutes} min</div>
            <div className="text-xs text-gray-400">MTTR</div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left Column - Network Status & Financial */}
        <div className="space-y-6">
          {/* Network Status Table */}
          <div className="bg-gray-800/70 rounded-lg border border-gray-700">
            <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
              <Globe className="w-4 h-4 text-blue-400" />
              <h2 className="font-semibold text-white">Network Status</h2>
            </div>
            <table className="w-full">
              <tbody className="divide-y divide-gray-700/50">
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2">
                    <span className="flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-green-400" />
                      <span className="text-gray-300">Operational</span>
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-green-400">{executiveSummary.healthy_nodes.toLocaleString()}</td>
                  <td className="px-4 py-2 text-right text-gray-500 text-xs">
                    {((executiveSummary.healthy_nodes / executiveSummary.total_nodes) * 100).toFixed(1)}%
                  </td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2">
                    <span className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-yellow-400" />
                      <span className="text-gray-300">Degraded</span>
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-yellow-400">{executiveSummary.degraded_nodes.toLocaleString()}</td>
                  <td className="px-4 py-2 text-right text-gray-500 text-xs">
                    {((executiveSummary.degraded_nodes / executiveSummary.total_nodes) * 100).toFixed(1)}%
                  </td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2">
                    <span className="flex items-center gap-2">
                      <XCircle className="w-4 h-4 text-red-400" />
                      <span className="text-gray-300">Outage</span>
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-red-400">{executiveSummary.outage_nodes.toLocaleString()}</td>
                  <td className="px-4 py-2 text-right text-gray-500 text-xs">
                    {((executiveSummary.outage_nodes / executiveSummary.total_nodes) * 100).toFixed(1)}%
                  </td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2">
                    <span className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-blue-400" />
                      <span className="text-gray-300">Maintenance</span>
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-blue-400">{executiveSummary.maintenance_nodes.toLocaleString()}</td>
                  <td className="px-4 py-2 text-right text-gray-500 text-xs">
                    {((executiveSummary.maintenance_nodes / executiveSummary.total_nodes) * 100).toFixed(1)}%
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Financial Summary Table */}
          <div className="bg-gray-800/70 rounded-lg border border-gray-700">
            <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-green-400" />
              <h2 className="font-semibold text-white">Financial Impact (30 days)</h2>
            </div>
            <table className="w-full">
              <tbody className="divide-y divide-gray-700/50">
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Revenue Protected</td>
                  <td className="px-4 py-2 text-right font-mono text-green-400">{formatCurrency(financialSummary.revenue_protected)}</td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Revenue Loss</td>
                  <td className="px-4 py-2 text-right font-mono text-red-400">{formatCurrency(financialSummary.actual_revenue_loss)}</td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">SLA Penalties</td>
                  <td className="px-4 py-2 text-right font-mono text-yellow-400">{formatCurrency(financialSummary.sla_penalties)}</td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">AI Cost Savings</td>
                  <td className="px-4 py-2 text-right font-mono text-purple-400">{formatCurrency(financialSummary.ai_savings)}</td>
                </tr>
                <tr className="bg-gray-700/30">
                  <td className="px-4 py-2 text-white font-medium">Net Impact</td>
                  <td className="px-4 py-2 text-right font-mono font-bold text-green-400">
                    {formatCurrency(financialSummary.revenue_protected - financialSummary.actual_revenue_loss + financialSummary.ai_savings)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Alert Summary */}
          <div className="bg-gray-800/70 rounded-lg border border-gray-700">
            <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-400" />
              <h2 className="font-semibold text-white">Alert Summary (24h)</h2>
            </div>
            <table className="w-full">
              <tbody className="divide-y divide-gray-700/50">
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Total Alerts</td>
                  <td className="px-4 py-2 text-right font-mono text-white">{executiveSummary.total_alerts.toLocaleString()}</td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Critical</td>
                  <td className="px-4 py-2 text-right font-mono text-red-400">{executiveSummary.critical_alerts.toLocaleString()}</td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Warning</td>
                  <td className="px-4 py-2 text-right font-mono text-yellow-400">{executiveSummary.warning_alerts.toLocaleString()}</td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Auto-Resolved</td>
                  <td className="px-4 py-2 text-right font-mono text-green-400">{executiveSummary.auto_resolved.toLocaleString()}</td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Manual Interventions</td>
                  <td className="px-4 py-2 text-right font-mono text-orange-400">{executiveSummary.manual_interventions.toLocaleString()}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Middle Column - Regional Performance & Period Comparison */}
        <div className="space-y-6">
          {/* Regional Performance Table */}
          <div className="bg-gray-800/70 rounded-lg border border-gray-700">
            <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-blue-400" />
                <h2 className="font-semibold text-white">Regional Performance</h2>
              </div>
              <span className="text-xs text-gray-500">{executiveSummary.regions.length} regions</span>
            </div>
            <table className="w-full">
              <thead className="bg-gray-900/50">
                <tr className="text-xs text-gray-400 uppercase">
                  <th className="px-4 py-2 text-left">Region</th>
                  <th className="px-4 py-2 text-right">Nodes</th>
                  <th className="px-4 py-2 text-right">Uptime</th>
                  <th className="px-4 py-2 text-right">Alerts</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/50">
                {displayedRegions.map((region: { region: string; nodes: number; uptime: number; revenue_impact: number; alerts: number }, index: number) => (
                  <tr key={index} className="hover:bg-gray-700/30">
                    <td className="px-4 py-2 text-gray-300">{region.region.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-2 text-right font-mono text-gray-400">{region.nodes}</td>
                    <td className="px-4 py-2 text-right">
                      <span className={`font-mono ${
                        region.uptime >= 99 ? 'text-green-400' :
                        region.uptime >= 95 ? 'text-yellow-400' : 'text-red-400'
                      }`}>
                        {formatPercent(region.uptime)}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-gray-400">{region.alerts.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {executiveSummary.regions.length > 5 && (
              <div className="px-4 py-2 border-t border-gray-700">
                <button
                  onClick={() => setShowAllRegions(!showAllRegions)}
                  className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                >
                  {showAllRegions ? (
                    <>Show less <ChevronUp className="w-3 h-3" /></>
                  ) : (
                    <>Show all {executiveSummary.regions.length} regions <ChevronDown className="w-3 h-3" /></>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* Period Comparison Table */}
          {executiveSummary.period_comparison && executiveSummary.period_comparison.length > 0 && (
            <div className="bg-gray-800/70 rounded-lg border border-gray-700">
              <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                <h2 className="font-semibold text-white">Period Comparison</h2>
                <span className="text-xs text-gray-500 ml-auto">vs Previous {executiveSummary.period_hours || 24}h</span>
              </div>
              <table className="w-full">
                <thead className="bg-gray-900/50">
                  <tr className="text-xs text-gray-400 uppercase">
                    <th className="px-4 py-2 text-left">Metric</th>
                    <th className="px-4 py-2 text-right">Current</th>
                    <th className="px-4 py-2 text-right">Previous</th>
                    <th className="px-4 py-2 text-right">Change</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/50">
                  {executiveSummary.period_comparison.map((comparison, index) => (
                    <tr key={index} className="hover:bg-gray-700/30">
                      <td className="px-4 py-2 text-gray-300">{formatMetricName(comparison.metric_name)}</td>
                      <td className="px-4 py-2 text-right font-mono text-white">{comparison.current_value.toFixed(2)}</td>
                      <td className="px-4 py-2 text-right font-mono text-gray-500">{comparison.previous_value.toFixed(2)}</td>
                      <td className="px-4 py-2 text-right">
                        <span className="flex items-center justify-end gap-1">
                          <span className={`font-mono text-xs ${
                            comparison.trend === 'improving' ? 'text-green-400' :
                            comparison.trend === 'declining' ? 'text-red-400' : 'text-gray-400'
                          }`}>
                            {comparison.change_percent > 0 ? '+' : ''}{comparison.change_percent.toFixed(2)}%
                          </span>
                          <TrendIcon trend={comparison.trend} size={12} />
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* KPI Performance */}
          <div className="bg-gray-800/70 rounded-lg border border-gray-700">
            <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-400" />
              <h2 className="font-semibold text-white">Network KPIs</h2>
            </div>
            <table className="w-full">
              <tbody className="divide-y divide-gray-700/50">
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Average Latency</td>
                  <td className="px-4 py-2 text-right">
                    <span className={`font-mono ${executiveSummary.avg_latency_ms <= 50 ? 'text-green-400' : 'text-yellow-400'}`}>
                      {executiveSummary.avg_latency_ms.toFixed(1)} ms
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Throughput</td>
                  <td className="px-4 py-2 text-right font-mono text-blue-400">
                    {executiveSummary.downstream_throughput_mbps.toFixed(1)} Mbps
                  </td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">DS SNR (Avg)</td>
                  <td className="px-4 py-2 text-right font-mono text-green-400">
                    {executiveSummary.avg_ds_snr_db.toFixed(1)} dB
                  </td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Affected Subscribers</td>
                  <td className="px-4 py-2 text-right">
                    <span className={`font-mono ${executiveSummary.affected_subscribers_current === 0 ? 'text-green-400' : 'text-yellow-400'}`}>
                      {executiveSummary.affected_subscribers_current.toLocaleString()}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column - AI Performance, Insights & Trends */}
        <div className="space-y-6">
          {/* AI Self-Healing Performance */}
          <div className="bg-gray-800/70 rounded-lg border border-gray-700">
            <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
              <Zap className="w-4 h-4 text-purple-400" />
              <h2 className="font-semibold text-white">AI Self-Healing</h2>
            </div>
            <table className="w-full">
              <tbody className="divide-y divide-gray-700/50">
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Auto-Resolved (24h)</td>
                  <td className="px-4 py-2 text-right font-mono text-green-400">{executiveSummary.auto_resolved.toLocaleString()}</td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Manual Interventions</td>
                  <td className="px-4 py-2 text-right font-mono text-yellow-400">{executiveSummary.manual_interventions.toLocaleString()}</td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Success Rate</td>
                  <td className="px-4 py-2 text-right font-mono text-green-400">
                    {executiveSummary.auto_resolved + executiveSummary.manual_interventions > 0
                      ? formatPercent((executiveSummary.auto_resolved / (executiveSummary.auto_resolved + executiveSummary.manual_interventions)) * 100)
                      : 'N/A'}
                  </td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">Avg Resolution Time</td>
                  <td className="px-4 py-2 text-right font-mono text-white">{executiveSummary.avg_resolution_time_minutes} min</td>
                </tr>
                <tr className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300">MTTR (Historical)</td>
                  <td className="px-4 py-2 text-right font-mono text-cyan-400">{executiveSummary.mttr_minutes?.toFixed(1) || 'N/A'} min</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Top Issues */}
          <div className="bg-gray-800/70 rounded-lg border border-gray-700">
            <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <h2 className="font-semibold text-white">Top Issues</h2>
            </div>
            <table className="w-full">
              <thead className="bg-gray-900/50">
                <tr className="text-xs text-gray-400 uppercase">
                  <th className="px-4 py-2 text-left">Issue Type</th>
                  <th className="px-4 py-2 text-right">Duration</th>
                  <th className="px-4 py-2 text-right">Impact</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/50">
                {executiveSummary.top_issues.map((issue: { node_id: string; issue_type: string; duration: number; impact: number }, index: number) => (
                  <tr key={index} className="hover:bg-gray-700/30">
                    <td className="px-4 py-2 text-gray-300">{issue.issue_type.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-2 text-right font-mono text-gray-400">{issue.duration}m</td>
                    <td className="px-4 py-2 text-right font-mono text-yellow-400">{formatCurrency(issue.impact)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* KPI Trend Chart */}
          {executiveSummary.kpi_trend_data && executiveSummary.kpi_trend_data.length > 0 && (
            <div className="bg-gray-800/70 rounded-lg border border-gray-700">
              <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-cyan-400" />
                <h2 className="font-semibold text-white">KPI Trends</h2>
                <span className="text-xs text-gray-500 ml-auto">{executiveSummary.kpi_trend_data.length} data points</span>
              </div>
              <div className="p-4">
                <KPITrendChart data={executiveSummary.kpi_trend_data} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* AI Insights Section */}
      {executiveSummary.ai_insights && executiveSummary.ai_insights.length > 0 && (
        <div className="bg-gray-800/70 rounded-lg border border-gray-700">
          <button
            onClick={() => setShowInsights(!showInsights)}
            className="w-full px-4 py-3 border-b border-gray-700 flex items-center justify-between hover:bg-gray-700/30"
          >
            <div className="flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-amber-400" />
              <h2 className="font-semibold text-white">AI Insights & Recommendations</h2>
              <span className="text-xs text-gray-500">({executiveSummary.ai_insights.length} insights)</span>
            </div>
            {showInsights ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
          </button>
          {showInsights && (
            <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              {executiveSummary.ai_insights.map((insight, index) => (
                <div
                  key={index}
                  className={`p-4 rounded-lg border ${
                    insight.severity === 'critical' ? 'bg-red-500/10 border-red-500/30' :
                    insight.severity === 'warning' ? 'bg-yellow-500/10 border-yellow-500/30' :
                    'bg-blue-500/10 border-blue-500/30'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <span className={`text-sm font-semibold ${
                      insight.severity === 'critical' ? 'text-red-400' :
                      insight.severity === 'warning' ? 'text-yellow-400' :
                      'text-blue-400'
                    }`}>
                      {insight.title}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      insight.severity === 'critical' ? 'bg-red-500/20 text-red-300' :
                      insight.severity === 'warning' ? 'bg-yellow-500/20 text-yellow-300' :
                      'bg-blue-500/20 text-blue-300'
                    }`}>
                      {insight.type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <p className="text-gray-300 text-sm mb-2">{insight.description}</p>
                  <div className="text-xs text-gray-400 border-t border-gray-600 pt-2 mt-2">
                    <span className="font-medium text-gray-300">Recommendation:</span> {insight.recommendation}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Report Footer */}
      <div className="text-center text-gray-500 text-xs flex items-center justify-center gap-4 flex-wrap border-t border-gray-700 pt-4">
        <span>Report Period: {executiveSummary.period} ({executiveSummary.period_hours || 24}h)</span>
        <span>|</span>
        <span>Uptime Trend: <span className={executiveSummary.trend_uptime === 'improving' ? 'text-green-400' : executiveSummary.trend_uptime === 'declining' ? 'text-red-400' : 'text-gray-400'}>{executiveSummary.trend_uptime}</span></span>
        <span>|</span>
        <span>Incident Trend: <span className={executiveSummary.trend_incidents === 'improving' ? 'text-green-400' : executiveSummary.trend_incidents === 'declining' ? 'text-red-400' : 'text-gray-400'}>{executiveSummary.trend_incidents}</span></span>
        {executiveSummary.data_source && (
          <>
            <span>|</span>
            <span className="flex items-center gap-1">
              <Database className="w-3 h-3" />
              Data Source: {executiveSummary.data_source}
            </span>
          </>
        )}
      </div>
    </div>
  );
});

ExecutiveView.displayName = 'ExecutiveView';

export default ExecutiveView;
