import { memo } from 'react';
import { NetworkHealthSummary } from '@/types';
import { Activity, AlertTriangle, CheckCircle, XCircle, Wrench } from 'lucide-react';
import { formatPercentage, formatNumber } from '@/utils/helpers';

interface NetworkHealthPanelProps {
  summary: NetworkHealthSummary;
}

const NetworkHealthPanel = memo(({ summary }: NetworkHealthPanelProps) => {
  const stats = [
    {
      label: 'Total Nodes',
      value: formatNumber(summary.total_nodes),
      icon: Activity,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      label: 'Healthy Nodes',
      value: `${formatNumber(summary.healthy_nodes)} (${formatPercentage((summary.healthy_nodes / summary.total_nodes) * 100)})`,
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      label: 'Degraded',
      value: formatNumber(summary.degraded_nodes),
      icon: AlertTriangle,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100',
    },
    {
      label: 'Outages',
      value: formatNumber(summary.outage_nodes),
      icon: XCircle,
      color: 'text-red-600',
      bgColor: 'bg-red-100',
    },
    {
      label: 'Active Alerts',
      value: formatNumber(summary.active_alerts),
      icon: AlertTriangle,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
      subtext: `${summary.critical_alerts} critical`,
    },
    {
      label: 'Self-Healing Actions (1h)',
      value: formatNumber(summary.self_healing_actions_last_hour),
      icon: Wrench,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
    },
    {
      label: 'Network Availability',
      value: formatPercentage(summary.network_availability),
      icon: Activity,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-100',
    },
    {
      label: 'Avg DS SNR',
      value: `${summary.avg_ds_snr_db.toFixed(1)} dB`,
      icon: CheckCircle,
      color: 'text-teal-600',
      bgColor: 'bg-teal-100',
    },
  ];

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6">
      <h2 className="text-lg font-semibold text-white mb-4">
        Network Health Summary
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-4">
        {stats.map((stat, index) => (
          <div key={index} className="text-center">
            <div className={`inline-flex p-3 rounded-full ${stat.bgColor} mb-2`}>
              <stat.icon className={`w-6 h-6 ${stat.color}`} />
            </div>
            <div className="text-2xl font-bold text-white">{stat.value}</div>
            <div className="text-xs text-gray-400 mt-1">{stat.label}</div>
            {stat.subtext && (
              <div className="text-xs text-gray-500 mt-0.5">{stat.subtext}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
});

NetworkHealthPanel.displayName = 'NetworkHealthPanel';

export default NetworkHealthPanel;
