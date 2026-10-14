import { memo, useState, useEffect } from 'react';
import {
  Database,
  Network,
  Brain,
  HardDrive,
  Activity,
  Monitor,
  ArrowDown,
  Layers,
  TrendingUp,
  Zap,
  Cloud,
  Server,
  GitBranch,
  Cpu
} from 'lucide-react';
import { DataFlowMetrics } from '@/services/dataFlowMetrics';

interface ArchitectureViewProps {
  nodes?: number;
  metrics?: DataFlowMetrics;
}

const ArchitectureView = memo(({ nodes = 1000, metrics }: ArchitectureViewProps) => {
  const [animating, setAnimating] = useState(false);
  const [activeLayer, setActiveLayer] = useState(0);

  // Animate data flow through layers
  useEffect(() => {
    let layerInterval: NodeJS.Timeout | null = null;
    let resetTimeout: NodeJS.Timeout | null = null;

    const interval = setInterval(() => {
      setAnimating(true);
      let layer = 0;

      layerInterval = setInterval(() => {
        setActiveLayer(layer);
        layer++;
        if (layer > 7) {
          if (layerInterval) clearInterval(layerInterval);
          layerInterval = null;
          resetTimeout = setTimeout(() => {
            setAnimating(false);
            setActiveLayer(0);
          }, 500);
        }
      }, 700);
    }, 9000);

    return () => {
      clearInterval(interval);
      if (layerInterval) clearInterval(layerInterval);
      if (resetTimeout) clearTimeout(resetTimeout);
    };
  }, []);

  const actualMetrics = metrics || {
    ingestionRate: Math.floor(nodes / 5),
    alertsGenerated: 0,
    actionsTriggered: 0,
    storageSize: 0,
  };

  // Calculate estimated throughput for production systems
  const estimatedThroughput = {
    nifiMBps: ((actualMetrics.ingestionRate * 0.4) / 1024).toFixed(2), // Assuming ~400 bytes per KPI
    kafkaMessagesPerSec: actualMetrics.ingestionRate,
    sparkRecordsPerSec: actualMetrics.ingestionRate,
    storageWritesPerSec: Math.floor(actualMetrics.ingestionRate / 10), // Batched writes
  };

  const layers = [
    {
      name: '1. Data Sources',
      tech: 'Real Fiber Node Network',
      icon: Network,
      description: 'Physical network infrastructure generating real-time telemetry',
      components: [
        'Base Stations (eNodeB/gNodeB)',
        'Radio Network Controllers',
        'Core Network Elements',
        'SNMP/Netconf Agents'
      ],
      metrics: [
        { label: 'Network Elements', value: nodes.toLocaleString() },
        { label: 'KPI Streams', value: '15+ per node' },
        { label: 'Collection Rate', value: '5s' },
      ],
      color: { bg: 'bg-blue-900/30', text: 'text-blue-400', border: 'border-blue-500', icon: 'bg-blue-500' },
      flow: 'Real nodes emit KPIs via SNMP, Netconf, or streaming APIs',
    },
    {
      name: '2. Data Ingestion',
      tech: 'Cloudera DataFlow (CDF) / Apache NiFi',
      icon: GitBranch,
      description: 'Enterprise data ingestion and routing platform',
      components: [
        'CDF Flow Designer',
        'GetSNMP Processors',
        'Schema Validation',
        'Data Enrichment'
      ],
      metrics: [
        { label: 'Throughput', value: `${estimatedThroughput.nifiMBps} MB/s` },
        { label: 'Processors', value: '20+' },
        { label: 'Flow Files/s', value: actualMetrics.ingestionRate.toString() },
      ],
      color: { bg: 'bg-cyan-900/30', text: 'text-cyan-400', border: 'border-cyan-500', icon: 'bg-cyan-500' },
      flow: 'Collects, validates, and routes telemetry to Kafka topics',
    },
    {
      name: '3. Message Streaming',
      tech: 'Apache Kafka 3.5+',
      icon: Zap,
      description: 'Distributed event streaming platform',
      components: [
        'kpi-metrics (Topic)',
        'network-events (Topic)',
        'alerts (Topic)',
        'actions (Topic)'
      ],
      metrics: [
        { label: 'Messages/s', value: estimatedThroughput.kafkaMessagesPerSec.toLocaleString() },
        { label: 'Topics', value: '4' },
        { label: 'Partitions', value: '24' },
      ],
      color: { bg: 'bg-purple-900/30', text: 'text-purple-400', border: 'border-purple-500', icon: 'bg-purple-500' },
      flow: 'Buffers and distributes events to downstream consumers',
    },
    {
      name: '4. Stream Processing',
      tech: 'Apache Flink / Spark Structured Streaming',
      icon: Cpu,
      description: 'Real-time stream processing and ML inference engine',
      components: [
        'Flink SQL & DataStream',
        'Spark Structured Streaming',
        'Anomaly Detection Models',
        'Windowed Aggregations'
      ],
      metrics: [
        { label: 'Records/s', value: estimatedThroughput.sparkRecordsPerSec.toLocaleString() },
        { label: 'Latency', value: '<100ms' },
        { label: 'ML Models', value: '3' },
      ],
      color: { bg: 'bg-orange-900/30', text: 'text-orange-400', border: 'border-orange-500', icon: 'bg-orange-500' },
      flow: 'Detects anomalies and generates alerts in real-time',
    },
    {
      name: '5. AI/ML Layer',
      tech: 'Cloudera Machine Learning + LLM',
      icon: Brain,
      description: 'Advanced analytics and intelligent decision making',
      components: [
        'Anomaly Detection (ML)',
        'Root Cause Analysis (LLM)',
        'Predictive Maintenance',
        'Remediation Planning'
      ],
      metrics: [
        { label: 'Alerts Generated', value: actualMetrics.alertsGenerated.toString() },
        { label: 'Model Accuracy', value: '94%' },
        { label: 'LLM Inference', value: '<500ms' },
      ],
      color: { bg: 'bg-pink-900/30', text: 'text-pink-400', border: 'border-pink-500', icon: 'bg-pink-500' },
      flow: 'ML models detect issues, LLM provides root cause and remediation',
    },
    {
      name: '6. Self-Healing Engine',
      tech: 'Remediation Orchestration Service',
      icon: Activity,
      description: 'Automated network remediation and optimization',
      components: [
        'Action Scheduler',
        'Network API Clients',
        'Rollback Manager',
        'Success Validation'
      ],
      metrics: [
        { label: 'Actions/hour', value: (actualMetrics.actionsTriggered * 6).toString() },
        { label: 'Success Rate', value: '87%' },
        { label: 'MTTR', value: '8 min' },
      ],
      color: { bg: 'bg-green-900/30', text: 'text-green-400', border: 'border-green-500', icon: 'bg-green-500' },
      flow: 'Executes remediation actions via network APIs',
    },
    {
      name: '7. Data Lake Storage',
      tech: 'Apache Kudu + Iceberg',
      icon: Database,
      description: 'Scalable columnar storage for analytics',
      components: [
        'Kudu Tables (Real-time)',
        'Iceberg Tables (Historical)',
        'S3/HDFS Backend',
        'Schema Evolution'
      ],
      metrics: [
        { label: 'Writes/s', value: estimatedThroughput.storageWritesPerSec.toString() },
        { label: 'Storage', value: `${(actualMetrics.storageSize * 100).toFixed(0)} GB` },
        { label: 'Retention', value: '90 days' },
      ],
      color: { bg: 'bg-yellow-900/30', text: 'text-yellow-400', border: 'border-yellow-500', icon: 'bg-yellow-500' },
      flow: 'Persists all data for historical analytics and compliance',
    },
    {
      name: '8. Visualization & BI',
      tech: 'Cloudera Data Visualization (CDV)',
      icon: Monitor,
      description: 'Native Cloudera dashboards and business intelligence',
      components: [
        'Real-time Dashboards',
        'Visual Analytics',
        'Custom Reports',
        'Embedded BI & REST APIs'
      ],
      metrics: [
        { label: 'Refresh Rate', value: '1-5s' },
        { label: 'Concurrent Users', value: '50+' },
        { label: 'Dashboards', value: '12' },
      ],
      color: { bg: 'bg-indigo-900/30', text: 'text-indigo-400', border: 'border-indigo-500', icon: 'bg-indigo-500' },
      flow: 'Provides insights to NOC engineers and executives',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              <Layers className="w-7 h-7 text-blue-400" />
              Production Architecture & Real-Time Data Flow
            </h2>
            <p className="text-gray-400 mt-2">
              Cloudera-native data pipeline for enterprise telco network monitoring
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${animating ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
            <span className="text-sm text-gray-400">
              {animating ? 'Data Flowing' : 'Idle'}
            </span>
          </div>
        </div>

        {/* Pipeline Stats - Simulating Production Scale */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-gray-700">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-400">{nodes}</div>
            <div className="text-xs text-gray-400 mt-1">Network Elements</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-400">
              {(actualMetrics.ingestionRate * 60).toLocaleString()}
            </div>
            <div className="text-xs text-gray-400 mt-1">Events per Minute</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400">{actualMetrics.actionsTriggered}</div>
            <div className="text-xs text-gray-400 mt-1">Auto-remediations</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-400">
              {(actualMetrics.storageSize * 100).toFixed(0)} GB
            </div>
            <div className="text-xs text-gray-400 mt-1">Data Lake Size</div>
          </div>
        </div>
      </div>

      {/* Cloudera Platform Components */}
      <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
          <Cloud className="w-5 h-5 text-blue-400" />
          Cloudera Data Platform Components
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div>
            <h4 className="font-medium text-cyan-400 mb-3 flex items-center gap-2">
              <Server className="w-4 h-4" />
              Data Engineering
            </h4>
            <ul className="space-y-2 text-sm text-gray-400">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-500"></div>
                Cloudera DataFlow (CDF)
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-500"></div>
                Apache NiFi / Kafka
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-500"></div>
                Schema Registry
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-medium text-orange-400 mb-3 flex items-center gap-2">
              <Cpu className="w-4 h-4" />
              Stream Processing
            </h4>
            <ul className="space-y-2 text-sm text-gray-400">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-orange-500"></div>
                Apache Flink
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-orange-500"></div>
                Spark Structured Streaming
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-orange-500"></div>
                Cloudera Streaming Analytics
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-medium text-yellow-400 mb-3 flex items-center gap-2">
              <Database className="w-4 h-4" />
              Data Storage
            </h4>
            <ul className="space-y-2 text-sm text-gray-400">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-yellow-500"></div>
                Apache Kudu 1.17+
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-yellow-500"></div>
                Apache Iceberg 1.4+
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-yellow-500"></div>
                S3/HDFS/ADLS
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-medium text-pink-400 mb-3 flex items-center gap-2">
              <Brain className="w-4 h-4" />
              AI/ML & Visualization
            </h4>
            <ul className="space-y-2 text-sm text-gray-400">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-pink-500"></div>
                Cloudera ML (CML)
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-pink-500"></div>
                Cloudera Data Visualization
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-pink-500"></div>
                Impala / Hive
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Architecture Benefits */}
      <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-6">
        <h4 className="text-lg font-semibold text-blue-300 mb-4 flex items-center gap-2">
          <HardDrive className="w-5 h-5" />
          Architecture Benefits
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Scalability */}
          <div className="space-y-3">
            <h5 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">Scalability</h5>
            <ul className="space-y-2 text-sm text-blue-200">
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Handles millions of events per second across distributed clusters</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Horizontal scaling with automatic load balancing</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Elastic resource allocation based on demand</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Support for 10,000+ concurrent node connections</span>
              </li>
            </ul>
          </div>

          {/* Fault Tolerance */}
          <div className="space-y-3">
            <h5 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">Fault Tolerance</h5>
            <ul className="space-y-2 text-sm text-blue-200">
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Kafka replication with 3x redundancy</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Spark checkpointing for stateful recovery</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Multi-region storage with automatic failover</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>99.99% uptime SLA guarantee</span>
              </li>
            </ul>
          </div>

          {/* Real-time Processing */}
          <div className="space-y-3">
            <h5 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">Real-time Processing</h5>
            <ul className="space-y-2 text-sm text-blue-200">
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Sub-second latency from ingestion to visualization</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Stream processing with Apache Flink/Spark</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Complex event processing for anomaly detection</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Real-time dashboards with live KPI updates</span>
              </li>
            </ul>
          </div>

          {/* ML at Scale */}
          <div className="space-y-3">
            <h5 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">ML at Scale</h5>
            <ul className="space-y-2 text-sm text-blue-200">
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Distributed model training on massive datasets</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Real-time inference with GPU acceleration</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Automated model retraining pipelines</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>MLOps with version control and A/B testing</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Additional Benefits Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6 pt-6 border-t border-blue-700/50">
          {/* Security & Compliance */}
          <div className="space-y-3">
            <h5 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">Security & Compliance</h5>
            <ul className="space-y-2 text-sm text-blue-200">
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>End-to-end encryption (TLS 1.3)</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Role-based access control (RBAC)</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>SOC 2 Type II compliant infrastructure</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Comprehensive audit logging</span>
              </li>
            </ul>
          </div>

          {/* Operational Excellence */}
          <div className="space-y-3">
            <h5 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">Operational Excellence</h5>
            <ul className="space-y-2 text-sm text-blue-200">
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Autonomous self-healing reduces MTTR by 85%</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Predictive maintenance prevents 70% of outages</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>AI-driven root cause analysis in seconds</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Automated crew dispatch and resource optimization</span>
              </li>
            </ul>
          </div>

          {/* Cost Efficiency */}
          <div className="space-y-3">
            <h5 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">Cost Efficiency</h5>
            <ul className="space-y-2 text-sm text-blue-200">
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>40% reduction in operational costs</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Optimized resource utilization via AI</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Reduced truck rolls with remote remediation</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400">•</span>
                <span>Pay-per-use cloud-native architecture</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Data Flow Layers */}
      <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-green-400" />
          End-to-End Production Data Pipeline
        </h3>

        <div className="space-y-4">
          {layers.map((layer, index) => (
            <div key={index} className="relative">
              {/* Layer Card */}
              <div
                className={`
                  ${layer.color.bg} ${layer.color.border}
                  border-2 rounded-lg p-5
                  transition-all duration-500
                  ${animating && activeLayer === index ? `shadow-xl shadow-${layer.color.icon}/50 scale-[1.02]` : 'shadow-sm'}
                `}
              >
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                  {/* Left: Icon and Name */}
                  <div className="flex items-start gap-4">
                    <div className={`${layer.color.icon} p-3 rounded-lg flex-shrink-0`}>
                      <layer.icon className="w-6 h-6 text-white" />
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-white font-semibold">{layer.name}</h4>
                      <p className={`text-sm ${layer.color.text} font-bold mt-1`}>
                        {layer.tech}
                      </p>
                      <p className="text-xs text-gray-500 mt-2 italic">
                        {layer.description}
                      </p>
                    </div>
                  </div>

                  {/* Middle: Components */}
                  <div className="lg:col-span-2 flex flex-wrap gap-2 items-start content-start">
                    {layer.components.map((component, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1.5 bg-gray-700 text-gray-300 text-xs rounded-md font-mono border border-gray-600"
                      >
                        {component}
                      </span>
                    ))}
                    <div className="w-full mt-2">
                      <p className="text-xs text-gray-400 italic">
                        → {layer.flow}
                      </p>
                    </div>
                  </div>

                  {/* Right: Metrics */}
                  <div className="space-y-2.5">
                    {layer.metrics.map((metric, idx) => (
                      <div key={idx} className="flex justify-between items-center bg-gray-900/50 rounded px-3 py-2">
                        <span className="text-gray-400 text-xs font-medium">{metric.label}:</span>
                        <span className={`${layer.color.text} text-sm font-mono font-bold`}>
                          {metric.value}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Flow Indicator */}
                {animating && activeLayer === index && (
                  <div className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 z-10">
                    <ArrowDown className={`w-6 h-6 ${layer.color.text} animate-bounce`} />
                  </div>
                )}
              </div>

              {/* Connector */}
              {index < layers.length - 1 && (
                <div className="flex justify-center my-2">
                  <div className={`w-0.5 h-8 ${animating && activeLayer === index ? layer.color.border : 'bg-gray-700'} transition-colors duration-300`}></div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
});

ArchitectureView.displayName = 'ArchitectureView';

export default ArchitectureView;
