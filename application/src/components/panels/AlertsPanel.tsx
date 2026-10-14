import { memo, useState, useMemo } from 'react';
import { Alert, AlertSeverity } from '@/types';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { formatTimestamp, getStatusColor } from '@/utils/helpers';

interface AlertsPanelProps {
  alerts: Alert[];
  onAlertClick: (alert: Alert) => void;
}

const AlertsPanel = memo(({ alerts, onAlertClick }: AlertsPanelProps) => {
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');

  const filteredAlerts = useMemo(() => {
    if (selectedSeverity === 'all') {
      return alerts;
    }
    return alerts.filter(alert => alert.severity === selectedSeverity);
  }, [alerts, selectedSeverity]);

  const getAlertIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return AlertCircle;
      case 'warning':
        return AlertTriangle;
      default:
        return Info;
    }
  };

  const severityCounts = useMemo(() => {
    const counts = {
      all: alerts.length,
      [AlertSeverity.CRITICAL]: 0,
      [AlertSeverity.WARNING]: 0,
    };
    alerts.forEach(alert => {
      if (alert.severity === AlertSeverity.CRITICAL) {
        counts[AlertSeverity.CRITICAL]++;
      } else if (alert.severity === AlertSeverity.WARNING) {
        counts[AlertSeverity.WARNING]++;
      }
    });
    return counts;
  }, [alerts]);

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6 h-full flex flex-col">
      <h2 className="text-lg font-semibold text-white mb-4">
        Active Alerts ({filteredAlerts.length})
      </h2>

      {/* Severity Filter */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setSelectedSeverity('all')}
          className={`px-3 py-1 text-xs rounded-full transition-colors ${
            selectedSeverity === 'all'
              ? 'bg-blue-600 text-white font-medium'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          All ({severityCounts.all})
        </button>
        <button
          onClick={() => setSelectedSeverity(AlertSeverity.CRITICAL)}
          className={`px-3 py-1 text-xs rounded-full transition-colors ${
            selectedSeverity === AlertSeverity.CRITICAL
              ? 'bg-red-600 text-white font-medium'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          Critical ({severityCounts[AlertSeverity.CRITICAL]})
        </button>
        <button
          onClick={() => setSelectedSeverity(AlertSeverity.WARNING)}
          className={`px-3 py-1 text-xs rounded-full transition-colors ${
            selectedSeverity === AlertSeverity.WARNING
              ? 'bg-yellow-600 text-white font-medium'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          Warning ({severityCounts[AlertSeverity.WARNING]})
        </button>
      </div>

      <div className="space-y-3 flex-1 overflow-y-auto">
        {filteredAlerts.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            {selectedSeverity === 'all' ? 'No active alerts' : `No ${selectedSeverity} alerts`}
          </p>
        ) : (
          filteredAlerts.slice(0, 10).map((alert) => {
            const Icon = getAlertIcon(alert.severity);
            return (
              <div
                key={alert.alert_id}
                onClick={() => onAlertClick(alert)}
                className="border border-gray-700 rounded-lg p-3 bg-gray-750 hover:bg-gray-700 cursor-pointer transition-colors"
              >
                <div className="flex items-start gap-3">
                  <Icon className={`w-5 h-5 ${getStatusColor(alert.severity).split(' ')[0]} flex-shrink-0 mt-0.5`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(alert.severity)}`}>
                        {alert.severity}
                      </span>
                      <span className="text-xs text-gray-400">{alert.node_id}</span>
                    </div>
                    <p className="text-sm text-white font-medium">{alert.description}</p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-gray-400">
                        {formatTimestamp(alert.timestamp)}
                      </span>
                      <span className="text-xs text-gray-400">
                        AI Confidence: {alert.ai_confidence.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
});

AlertsPanel.displayName = 'AlertsPanel';

export default AlertsPanel;
