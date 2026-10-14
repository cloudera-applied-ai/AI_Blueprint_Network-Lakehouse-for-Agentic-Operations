import { memo, useMemo, useState } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, YAxis, XAxis } from 'recharts';
import { AggregatedKPITrends, KPICurrentValues } from '@/services/kpiAggregator';
import { Region } from '@/types';

interface HorizontalKPIPanelProps {
  trends: AggregatedKPITrends;
  current: KPICurrentValues;
  onFilterChange?: (filter: FilterType) => void;
}

export type FilterType = 'all' | Region;

const HorizontalKPIPanel = memo(({ trends, current, onFilterChange }: HorizontalKPIPanelProps) => {
  const [selectedFilter, setSelectedFilter] = useState<FilterType>('all');

  const handleFilterChange = (filter: FilterType) => {
    setSelectedFilter(filter);
    onFilterChange?.(filter);
  };

  const metrics = useMemo(() => {
    // Calculate trends by comparing first and last values
    const getTrend = (data: { timestamp: number; value: number }[]): 'up' | 'down' | 'stable' => {
      if (data.length < 2) return 'stable';
      const first = data[0].value;
      const last = data[data.length - 1].value;
      const change = ((last - first) / first) * 100;
      if (change > 2) return 'up';
      if (change < -2) return 'down';
      return 'stable';
    };

    return [
      {
        label: 'DS SNR',
        value: `${current.ds_snr_db.toFixed(1)} dB`,
        trend: getTrend(trends.ds_snr_db),
        color: current.ds_snr_db >= 33 ? 'text-green-500' : current.ds_snr_db >= 28 ? 'text-yellow-500' : 'text-red-500',
        chartData: trends.ds_snr_db,
        chartColor: current.ds_snr_db >= 33 ? '#10b981' : current.ds_snr_db >= 28 ? '#eab308' : '#ef4444',
        domain: [20, 45] as [number, number],
      },
      {
        label: 'Downstream Throughput',
        value: `${current.downstream_throughput_mbps.toFixed(0)} Mbps`,
        trend: getTrend(trends.downstream_throughput_mbps),
        color: 'text-blue-500',
        chartData: trends.downstream_throughput_mbps,
        chartColor: '#3b82f6',
        domain: [0, 'auto'] as [number, string],
      },
      {
        label: 'Packet Loss',
        value: `${current.packet_loss_percent.toFixed(2)}%`,
        trend: getTrend(trends.packet_loss_percent),
        color: current.packet_loss_percent <= 2 ? 'text-green-500' : current.packet_loss_percent <= 4 ? 'text-yellow-500' : 'text-red-500',
        chartData: trends.packet_loss_percent,
        chartColor: current.packet_loss_percent <= 2 ? '#10b981' : current.packet_loss_percent <= 4 ? '#eab308' : '#ef4444',
        domain: [0, 10] as [number, number],
        invertTrend: true, // Lower is better
      },
      {
        label: 'Latency',
        value: `${current.latency_ms.toFixed(1)} ms`,
        trend: getTrend(trends.latency_ms),
        color: current.latency_ms <= 30 ? 'text-green-500' : current.latency_ms <= 60 ? 'text-yellow-500' : 'text-red-500',
        chartData: trends.latency_ms,
        chartColor: current.latency_ms <= 30 ? '#10b981' : current.latency_ms <= 60 ? '#eab308' : '#ef4444',
        domain: [0, 100] as [number, number],
        invertTrend: true, // Lower is better
      },
    ];
  }, [trends, current]);

  const getTrendIcon = (trend: 'up' | 'down' | 'stable', invertTrend?: boolean) => {
    if (trend === 'stable') return Minus;

    // For metrics where lower is better (like call drop rate), invert the icon
    if (invertTrend) {
      return trend === 'down' ? TrendingUp : TrendingDown;
    }
    return trend === 'up' ? TrendingUp : TrendingDown;
  };

  const filterOptions: { value: FilterType; label: string }[] = [
    { value: 'all', label: 'All Regions' },
    { value: Region.NORTHEAST, label: 'Northeast US' },
    { value: Region.SOUTHEAST, label: 'Southeast US' },
    { value: Region.MIDWEST, label: 'Midwest US' },
    { value: Region.SOUTH_CENTRAL, label: 'South Central US' },
    { value: Region.MOUNTAIN, label: 'Mountain US' },
    { value: Region.PACIFIC, label: 'Pacific US' },
    { value: Region.CANADA, label: 'Canada' },
    { value: Region.LATIN_AMERICA, label: 'Latin America' },
    { value: Region.EUROPE, label: 'Europe' },
    { value: Region.MIDDLE_EAST, label: 'Middle East' },
    { value: Region.APAC, label: 'Asia Pacific' },
    { value: Region.OCEANIA, label: 'Oceania' },
    { value: Region.AFRICA, label: 'Africa' },
  ];

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6">
      {/* Header with Filter */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-white">Real-Time KPI Trends</h2>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-400">Region:</label>
          <select
            value={selectedFilter}
            onChange={(e) => handleFilterChange(e.target.value as FilterType)}
            className="bg-gray-700 text-white text-sm rounded-md px-3 py-1.5 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {filterOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Horizontal KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((metric, index) => {
          const TrendIcon = getTrendIcon(metric.trend, metric.invertTrend);
          return (
            <div key={index} className="bg-gray-900 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-400">{metric.label}</span>
                <TrendIcon className={`w-4 h-4 ${metric.color}`} />
              </div>
              <div className={`text-2xl font-bold ${metric.color} mb-3`}>{metric.value}</div>
              <div className="h-16">
                {metric.chartData.length >= 2 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={metric.chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                      <XAxis dataKey="timestamp" hide />
                      <YAxis domain={metric.domain} hide />
                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke={metric.chartColor}
                        strokeWidth={2.5}
                        dot={metric.chartData.length < 10 ? { fill: metric.chartColor, r: 3 } : false}
                        isAnimationActive={false}
                        connectNulls={true}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full bg-gray-800 rounded flex items-center justify-center text-xs text-gray-500">
                    Collecting data... ({metric.chartData.length} points)
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});

HorizontalKPIPanel.displayName = 'HorizontalKPIPanel';

export default HorizontalKPIPanel;
