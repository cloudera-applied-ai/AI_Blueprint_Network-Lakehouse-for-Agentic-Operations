import { memo, useState, useEffect } from 'react';
import { Database, Activity, Brain, HardDrive, BarChart3, Monitor, ArrowRight, Zap } from 'lucide-react';

interface DataFlowMetrics {
  ingestionRate: number; // KPIs per second
  alertsGenerated: number;
  actionsTriggered: number;
  storageSize: number; // MB
  processingLatency: number; // ms
  activeConnections: number;
}

interface DataFlowDiagramProps {
  nodes: number;
  metrics?: DataFlowMetrics;
}

const DataFlowDiagram = memo(({ nodes, metrics }: DataFlowDiagramProps) => {
  const [animating, setAnimating] = useState(false);

  // Trigger animation periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setAnimating(true);
      setTimeout(() => setAnimating(false), 2000);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const defaultMetrics: DataFlowMetrics = {
    ingestionRate: Math.floor(nodes / 5), // 2000 nodes / 5 seconds = 400/sec
    alertsGenerated: 0,
    actionsTriggered: 0,
    storageSize: 0,
    processingLatency: 0,
    activeConnections: nodes,
  };

  const currentMetrics = metrics || defaultMetrics;

  const stages = [
    {
      id: 'ingestion',
      icon: Database,
      title: 'Data Ingestion',
      description: 'Fiber Node KPIs',
      metrics: [
        { label: 'Nodes', value: nodes.toLocaleString() },
        { label: 'Rate', value: `${currentMetrics.ingestionRate}/sec` },
      ],
      color: 'blue',
    },
    {
      id: 'processing',
      icon: Brain,
      title: 'AI Processing',
      description: 'Anomaly Detection',
      metrics: [
        { label: 'Alerts', value: currentMetrics.alertsGenerated.toLocaleString() },
        { label: 'Latency', value: `${currentMetrics.processingLatency}ms` },
      ],
      color: 'purple',
    },
    {
      id: 'healing',
      icon: Activity,
      title: 'Self-Healing',
      description: 'Auto Remediation',
      metrics: [
        { label: 'Actions', value: currentMetrics.actionsTriggered.toLocaleString() },
        { label: 'Success', value: '85%' },
      ],
      color: 'green',
    },
    {
      id: 'storage',
      icon: HardDrive,
      title: 'Storage Layer',
      description: 'Memory + IndexedDB',
      metrics: [
        { label: 'Size', value: `${currentMetrics.storageSize.toFixed(1)} MB` },
        { label: 'Persistent', value: 'Active' },
      ],
      color: 'yellow',
    },
    {
      id: 'analytics',
      icon: BarChart3,
      title: 'Analytics',
      description: 'KPI Aggregation',
      metrics: [
        { label: 'Metrics', value: '6 KPIs' },
        { label: 'Window', value: '60s' },
      ],
      color: 'cyan',
    },
    {
      id: 'visualization',
      icon: Monitor,
      title: 'Visualization',
      description: 'Dashboard & Maps',
      metrics: [
        { label: 'Refresh', value: '1s' },
        { label: 'Regions', value: '6' },
      ],
      color: 'pink',
    },
  ];

  const getColorClasses = (color: string) => {
    const colors: Record<string, { bg: string; text: string; border: string; glow: string }> = {
      blue: { bg: 'bg-blue-900/30', text: 'text-blue-400', border: 'border-blue-500', glow: 'shadow-blue-500/50' },
      purple: { bg: 'bg-purple-900/30', text: 'text-purple-400', border: 'border-purple-500', glow: 'shadow-purple-500/50' },
      green: { bg: 'bg-green-900/30', text: 'text-green-400', border: 'border-green-500', glow: 'shadow-green-500/50' },
      yellow: { bg: 'bg-yellow-900/30', text: 'text-yellow-400', border: 'border-yellow-500', glow: 'shadow-yellow-500/50' },
      cyan: { bg: 'bg-cyan-900/30', text: 'text-cyan-400', border: 'border-cyan-500', glow: 'shadow-cyan-500/50' },
      pink: { bg: 'bg-pink-900/30', text: 'text-pink-400', border: 'border-pink-500', glow: 'shadow-pink-500/50' },
    };
    return colors[color];
  };

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-400" />
            Data Architecture & Real-Time Flow
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            End-to-end data pipeline with live metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${animating ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
          <span className="text-xs text-gray-400">
            {animating ? 'Data Flowing' : 'Idle'}
          </span>
        </div>
      </div>

      {/* Data Flow Stages */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {stages.map((stage, index) => {
          const colors = getColorClasses(stage.color);
          const Icon = stage.icon;

          return (
            <div key={stage.id} className="relative">
              {/* Stage Card */}
              <div
                className={`
                  ${colors.bg} ${colors.border}
                  border rounded-lg p-4 h-full
                  transition-all duration-300
                  ${animating ? `shadow-lg ${colors.glow}` : 'shadow-sm'}
                  hover:shadow-lg hover:${colors.glow}
                `}
              >
                {/* Icon */}
                <div className={`${colors.text} mb-3`}>
                  <Icon className="w-6 h-6" />
                </div>

                {/* Title */}
                <h3 className="text-white font-semibold text-sm mb-1">
                  {stage.title}
                </h3>
                <p className="text-gray-400 text-xs mb-3">
                  {stage.description}
                </p>

                {/* Metrics */}
                <div className="space-y-1.5">
                  {stage.metrics.map((metric, idx) => (
                    <div key={idx} className="flex justify-between items-center">
                      <span className="text-gray-500 text-xs">{metric.label}:</span>
                      <span className={`${colors.text} text-xs font-mono font-semibold`}>
                        {metric.value}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Data Flow Animation */}
                {animating && index < stages.length - 1 && (
                  <div className="absolute -right-2 top-1/2 transform -translate-y-1/2 z-10">
                    <div className={`${colors.text} animate-ping absolute`}>
                      <ArrowRight className="w-4 h-4" />
                    </div>
                    <div className={colors.text}>
                      <ArrowRight className="w-4 h-4" />
                    </div>
                  </div>
                )}
              </div>

              {/* Arrow connector (desktop) */}
              {index < stages.length - 1 && (
                <div className="hidden xl:block absolute -right-2 top-1/2 transform -translate-y-1/2 z-0">
                  <ArrowRight className="w-4 h-4 text-gray-600" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Pipeline Statistics */}
      <div className="mt-6 pt-6 border-t border-gray-700">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-blue-400">
              {(currentMetrics.ingestionRate * 60).toLocaleString()}
            </div>
            <div className="text-xs text-gray-400 mt-1">KPIs/min</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-400">
              {currentMetrics.alertsGenerated}
            </div>
            <div className="text-xs text-gray-400 mt-1">Active Alerts</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-400">
              {currentMetrics.actionsTriggered}
            </div>
            <div className="text-xs text-gray-400 mt-1">Healing Actions</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-cyan-400">
              {currentMetrics.activeConnections}
            </div>
            <div className="text-xs text-gray-400 mt-1">Active Nodes</div>
          </div>
        </div>
      </div>
    </div>
  );
});

DataFlowDiagram.displayName = 'DataFlowDiagram';

export default DataFlowDiagram;
