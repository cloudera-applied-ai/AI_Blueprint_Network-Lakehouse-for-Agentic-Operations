/**
 * Node Status Report Modal - AI-powered comprehensive node analysis
 * Displays detailed status report with performance metrics interpretation
 */

import { memo, useState, useEffect, useCallback } from 'react';
import { FiberNode } from '@/types';
import {
  X,
  Activity,
  BarChart2,
  AlertTriangle,
  Wrench,
  Server,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  CheckCircle2,
  XCircle,
  Brain,
  RefreshCw,
  FileText,
  ChevronDown,
  ChevronUp,
  Zap,
  Shield,
  Calendar,
  Radio,
  Cpu,
  Fan,
  Battery,
  Cloud,
  CloudRain,
  CloudSnow,
  CloudLightning,
  Sun,
  Wind,
  Thermometer,
  Droplets,
} from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, YAxis, XAxis, Tooltip } from 'recharts';
import { nodeAnalysisService, NodeAnalysisReport } from '@/services/nodeAnalysisService';
import { llmService } from '@/services/llmService';
import { apiClient } from '@/services/apiClient';

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

interface NodeStatusReportModalProps {
  node: FiberNode;
  onClose: () => void;
}

/**
 * Safely convert a date value (string or Date) to a localized string.
 */
function toDateString(value: Date | string | undefined | null): string {
  if (!value) return 'Unknown';
  try {
    const date = value instanceof Date ? value : new Date(value);
    if (isNaN(date.getTime())) return 'Invalid date';
    return date.toLocaleString();
  } catch {
    return 'Invalid date';
  }
}

/**
 * Safely format a number, returning fallback for NaN/undefined/null.
 */
function safeNumber(value: number | undefined | null, decimals: number = 0, fallback: string = 'N/A'): string {
  if (value === undefined || value === null || isNaN(value)) return fallback;
  return value.toFixed(decimals);
}

/**
 * Safely convert an LLM array item to a displayable string.
 * LLM sometimes returns objects like {metric, value, status, reason} instead of strings.
 */
function toDisplayString(item: unknown, depth: number = 0): string {
  if (typeof item === 'string') {
    return item;
  }
  if (item === null || item === undefined) {
    return '';
  }
  if (Array.isArray(item)) {
    // Convert arrays to bullet-separated list
    return item.map(i => toDisplayString(i, depth + 1)).filter(Boolean).join('; ');
  }
  if (typeof item === 'object') {
    // Handle common LLM object structures
    const obj = item as Record<string, unknown>;
    // Try to build a meaningful string from common fields
    const parts: string[] = [];

    // Priority fields - these are the most descriptive
    const priorityFields = ['summary', 'analysis', 'assessment', 'overview', 'conclusion'];
    for (const field of priorityFields) {
      if (obj[field] && typeof obj[field] === 'string') {
        return String(obj[field]);
      }
    }

    // Common text fields
    if (obj.metric) parts.push(String(obj.metric));
    if (obj.name) parts.push(String(obj.name));
    if (obj.title) parts.push(String(obj.title));
    if (obj.value !== undefined) parts.push(`${obj.value}`);
    if (obj.status) parts.push(String(obj.status));
    if (obj.reason) parts.push(String(obj.reason));
    if (obj.message) parts.push(String(obj.message));
    if (obj.description) parts.push(String(obj.description));
    if (obj.issue) parts.push(String(obj.issue));
    if (obj.recommendation) parts.push(String(obj.recommendation));
    if (obj.finding) parts.push(String(obj.finding));
    if (obj.action) parts.push(String(obj.action));
    if (obj.text) parts.push(String(obj.text));
    if (obj.details) parts.push(String(obj.details));
    if (obj.explanation) parts.push(String(obj.explanation));
    if (obj.insight) parts.push(String(obj.insight));
    if (obj.trend) parts.push(`Trend: ${obj.trend}`);
    if (obj.severity) parts.push(`Severity: ${obj.severity}`);
    if (obj.impact) parts.push(String(obj.impact));
    if (obj.cause) parts.push(String(obj.cause));
    if (obj.solution) parts.push(String(obj.solution));

    if (parts.length > 0) {
      return parts.join(' - ');
    }

    // If no known fields found, try to extract values from all string fields (avoid deep recursion)
    if (depth < 2) {
      const stringValues = Object.entries(obj)
        .filter(([_, v]) => typeof v === 'string' && v.length > 0 && v.length < 500)
        .map(([k, v]) => `${k}: ${v}`);
      if (stringValues.length > 0) {
        return stringValues.slice(0, 3).join('; ');
      }
    }

    // Last resort - return a simplified representation instead of raw JSON
    const keys = Object.keys(obj);
    if (keys.length === 0) return '';
    return `[Analysis data with ${keys.length} fields]`;
  }
  // Numbers, booleans, etc.
  return String(item);
}

const NodeStatusReportModal = memo(({ node, onClose }: NodeStatusReportModalProps) => {
  const [report, setReport] = useState<NodeAnalysisReport | null>(null);
  const [progress, setProgress] = useState<{ stage: string; percent: number }>({
    stage: 'Initializing...',
    percent: 0,
  });
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['executive', 'performance', 'equipment'])
  );
  const [equipmentHistory, setEquipmentHistory] = useState<EquipmentHistoryResponse | null>(null);
  const [nodeWeather, setNodeWeather] = useState<{
    weather_conditions: string | null;
    weather_impact: number | null;
    temperature_outdoor: number | null;
    precipitation_mm: number | null;
    wind_speed_kmh: number | null;
    last_updated: string | null;
  } | null>(null);

  // Fetch weather data for node
  useEffect(() => {
    const fetchWeather = async () => {
      try {
        const response = await fetch(`/api/v1/weather/node/${node.node_id}`);
        if (response.ok) {
          const data = await response.json();
          setNodeWeather(data);
        }
      } catch (error) {
        console.error('Failed to fetch node weather:', error);
      }
    };
    fetchWeather();
  }, [node.node_id]);

  // Generate report and fetch equipment history on mount or when node changes
  useEffect(() => {
    console.log(`[NodeStatusReportModal] useEffect triggered for node: ${node.node_id}`);
    let isCancelled = false;

    // Reset state for new node
    setReport(null);
    setEquipmentHistory(null);
    setProgress({ stage: 'Initializing...', percent: 0 });

    const generateReport = async () => {
      console.log(`[NodeStatusReportModal] Starting report generation for: ${node.node_id}`);
      try {
        const result = await nodeAnalysisService.generateNodeReport(
          node,
          (stage, percent) => {
            if (!isCancelled) {
              setProgress({ stage, percent });
            }
          }
        );
        if (!isCancelled) {
          console.log(`[NodeStatusReportModal] Report generated for: ${node.node_id}, status: ${result.analysisStatus}`);
          setReport(result);
        } else {
          console.log(`[NodeStatusReportModal] Report generation cancelled for: ${node.node_id} (node changed)`);
        }
      } catch (error) {
        console.error(`[NodeStatusReportModal] Error generating report for ${node.node_id}:`, error);
        if (!isCancelled) {
          setReport({
            nodeId: node.node_id,
            nodeName: `${node.city} - ${node.node_id}`,
            generatedAt: new Date(),
            analysisStatus: 'error',
            error: error instanceof Error ? error.message : 'Unknown error',
            executiveSummary: { overallHealth: 'critical', healthScore: 0, keyFindings: [], urgentIssues: [], recommendations: [] },
            performanceAnalysis: { summary: '', kpiTrends: [], anomalies: [], comparisonToFleet: '' },
            equipmentStatus: { summary: '', hardwareHealth: '', firmwareStatus: '', maintenanceNeeds: [], endOfLifeWarnings: [] },
            alertAnalysis: { totalAlerts: 0, criticalAlerts: 0, warningAlerts: 0, resolvedAlerts: 0, activeAlerts: 0, commonIssues: [], patternAnalysis: '', alertList: [] },
            remediationAnalysis: { totalActions: 0, successRate: 0, avgResolutionTime: '', mostEffectiveActions: [], failedActions: 0, improvementSuggestions: [] },
            predictiveInsights: { riskScore: 0, potentialIssues: [], maintenanceRecommendations: [], capacityForecast: '' },
            rawDataSummary: { kpiRecordsAnalyzed: 0, alertsAnalyzed: 0, actionsAnalyzed: 0, timeRangeStart: new Date(), timeRangeEnd: new Date() },
          });
        }
      }
    };

    const fetchEquipmentHistory = async () => {
      try {
        const history = await apiClient.get<EquipmentHistoryResponse>(
          `/nodes/${node.node_id}/equipment/history?days=7`
        );
        if (!isCancelled) {
          setEquipmentHistory(history);
        }
      } catch (error) {
        console.error('[NodeStatusReportModal] Failed to fetch equipment history:', error);
      }
    };

    generateReport();
    fetchEquipmentHistory();

    // Cleanup function to prevent state updates on unmounted component
    return () => {
      console.log(`[NodeStatusReportModal] Cleanup for node: ${node.node_id}`);
      isCancelled = true;
    };
  }, [node.node_id]); // Use node_id as dependency for more reliable triggering

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

  const toggleSection = useCallback((section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  }, []);

  const regenerateReport = useCallback(async () => {
    setReport(null);
    setProgress({ stage: 'Initializing...', percent: 0 });
    const result = await nodeAnalysisService.generateNodeReport(
      node,
      (stage: string, percent: number) => setProgress({ stage, percent })
    );
    setReport(result);
  }, [node]);

  // Health color mapping
  const getHealthColor = (health: string) => {
    switch (health) {
      case 'excellent': return 'text-green-400 bg-green-900/30';
      case 'good': return 'text-blue-400 bg-blue-900/30';
      case 'fair': return 'text-yellow-400 bg-yellow-900/30';
      case 'poor': return 'text-orange-400 bg-orange-900/30';
      case 'critical': return 'text-red-400 bg-red-900/30';
      default: return 'text-gray-400 bg-gray-900/30';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving': return <TrendingUp className="w-4 h-4 text-green-400" />;
      case 'declining': return <TrendingDown className="w-4 h-4 text-red-400" />;
      default: return <Minus className="w-4 h-4 text-gray-400" />;
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 70) return 'text-red-400';
    if (score >= 40) return 'text-yellow-400';
    return 'text-green-400';
  };

  // Section header component
  const SectionHeader = ({
    title,
    icon,
    section,
    badge,
  }: {
    title: string;
    icon: React.ReactNode;
    section: string;
    badge?: string | number;
  }) => (
    <button
      onClick={() => toggleSection(section)}
      className="w-full flex items-center justify-between p-3 bg-gray-700 hover:bg-gray-650 rounded-lg transition-colors"
    >
      <div className="flex items-center gap-2">
        {icon}
        <span className="font-semibold text-gray-200">{title}</span>
        {badge !== undefined && (
          <span className="px-2 py-0.5 bg-gray-600 rounded text-xs text-gray-300">{badge}</span>
        )}
      </div>
      {expandedSections.has(section) ? (
        <ChevronUp className="w-5 h-5 text-gray-400" />
      ) : (
        <ChevronDown className="w-5 h-5 text-gray-400" />
      )}
    </button>
  );

  // Loading state
  if (!report) {
    return (
      <div
        className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center p-4"
        style={{ zIndex: 9999 }}
        onClick={handleBackdropClick}
      >
        <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-lg p-8 border border-gray-700">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Brain className="w-8 h-8 text-blue-400 animate-pulse" />
              <div>
                <h2 className="text-xl font-bold text-white">AI Node Analysis</h2>
                <p className="text-sm text-gray-400">{node.node_id}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-300 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="space-y-4">
            <div className="text-center">
              <div className="inline-flex items-center gap-2 text-blue-400 mb-4">
                <RefreshCw className="w-5 h-5 animate-spin" />
                <span>{progress.stage}</span>
              </div>
            </div>

            <div className="w-full bg-gray-700 rounded-full h-3">
              <div
                className="bg-blue-500 h-3 rounded-full transition-all duration-300"
                style={{ width: `${progress.percent}%` }}
              ></div>
            </div>

            <div className="text-center text-sm text-gray-400">
              {progress.percent}% complete
            </div>

            {llmService.isEnabled() ? (
              <div className="flex items-center justify-center gap-2 text-xs text-green-400">
                <CheckCircle2 className="w-4 h-4" />
                AI Analysis Enabled
              </div>
            ) : (
              <div className="flex items-center justify-center gap-2 text-xs text-yellow-400">
                <AlertTriangle className="w-4 h-4" />
                Using Rule-Based Analysis (LLM not configured)
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (report.analysisStatus === 'error') {
    return (
      <div
        className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center p-4"
        style={{ zIndex: 9999 }}
        onClick={handleBackdropClick}
      >
        <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-lg p-8 border border-red-700">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <XCircle className="w-8 h-8 text-red-400" />
              <div>
                <h2 className="text-xl font-bold text-white">Analysis Failed</h2>
                <p className="text-sm text-gray-400">{node.node_id}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-300 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="text-center space-y-4">
            <p className="text-red-400">{report.error || 'Unknown error occurred'}</p>
            <button
              onClick={regenerateReport}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Retry Analysis
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Main report view
  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center p-4"
      style={{ zIndex: 9999 }}
      onClick={handleBackdropClick}
    >
      <div
        className="bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden border border-gray-700 flex flex-col"
        style={{ position: 'relative', zIndex: 10000 }}
      >
        {/* Header */}
        <div className="sticky top-0 bg-gray-800 border-b border-gray-700 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <Brain className="w-8 h-8 text-blue-400" />
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                AI Node Analysis
                <span className={`px-2 py-0.5 rounded text-sm font-medium ${getHealthColor(report.executiveSummary.overallHealth)}`}>
                  {report.executiveSummary.overallHealth.toUpperCase()}
                </span>
              </h2>
              <p className="text-sm text-gray-400">
                {node.node_id} - {node.city}, {node.region}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={regenerateReport}
              className="p-2 text-gray-400 hover:text-gray-300 transition-colors"
              title="Regenerate Report"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-300 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1 p-6 space-y-4">
          {/* Health Score Card */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-700 rounded-lg p-4 text-center border border-gray-600">
              <div className={`text-3xl font-bold ${
                report.executiveSummary.healthScore >= 75 ? 'text-green-400' :
                report.executiveSummary.healthScore >= 50 ? 'text-yellow-400' :
                'text-red-400'
              }`}>
                {report.executiveSummary.healthScore}
              </div>
              <div className="text-xs text-gray-400 mt-1">Health Score</div>
            </div>
            <div className="bg-gray-700 rounded-lg p-4 text-center border border-gray-600">
              <div className={`text-3xl font-bold ${getRiskColor(report.predictiveInsights.riskScore)}`}>
                {report.predictiveInsights.riskScore}
              </div>
              <div className="text-xs text-gray-400 mt-1">Risk Score</div>
            </div>
            <div className="bg-gray-700 rounded-lg p-4 text-center border border-gray-600">
              <div className="text-3xl font-bold text-blue-400">
                {safeNumber(report.remediationAnalysis.successRate, 0, '0')}%
              </div>
              <div className="text-xs text-gray-400 mt-1">Remediation Success</div>
            </div>
            <div className="bg-gray-700 rounded-lg p-4 text-center border border-gray-600">
              <div className={`text-3xl font-bold ${
                report.alertAnalysis.activeAlerts > 0 ? 'text-orange-400' : 'text-green-400'
              }`}>
                {report.alertAnalysis.activeAlerts}
              </div>
              <div className="text-xs text-gray-400 mt-1">Active Alerts</div>
            </div>
          </div>

          {/* Weather Card - Full Width */}
          {nodeWeather && nodeWeather.weather_conditions && (
            <div className="bg-gray-700 rounded-lg p-4 border border-gray-600">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {/* Weather Icon */}
                  {nodeWeather.weather_conditions.toLowerCase().includes('thunder') || nodeWeather.weather_conditions.toLowerCase().includes('storm') ? (
                    <CloudLightning className="w-8 h-8 text-yellow-400" />
                  ) : nodeWeather.weather_conditions.toLowerCase().includes('snow') ? (
                    <CloudSnow className="w-8 h-8 text-blue-300" />
                  ) : nodeWeather.weather_conditions.toLowerCase().includes('rain') || nodeWeather.weather_conditions.toLowerCase().includes('drizzle') ? (
                    <CloudRain className="w-8 h-8 text-blue-400" />
                  ) : nodeWeather.weather_conditions.toLowerCase().includes('clear') ? (
                    <Sun className="w-8 h-8 text-yellow-300" />
                  ) : (
                    <Cloud className="w-8 h-8 text-gray-300" />
                  )}
                  <div>
                    <div className="text-lg font-semibold text-white">{nodeWeather.weather_conditions}</div>
                    <div className="text-xs text-gray-400">Current Weather at Node Location</div>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  {/* Temperature */}
                  {nodeWeather.temperature_outdoor !== null && (
                    <div className="flex items-center gap-2">
                      <Thermometer className="w-5 h-5 text-orange-400" />
                      <div>
                        <div className="text-xl font-bold text-white">{nodeWeather.temperature_outdoor.toFixed(1)}°C</div>
                        <div className="text-xs text-gray-400">Outdoor</div>
                      </div>
                    </div>
                  )}
                  {/* Wind */}
                  {nodeWeather.wind_speed_kmh !== null && nodeWeather.wind_speed_kmh > 0 && (
                    <div className="flex items-center gap-2">
                      <Wind className="w-5 h-5 text-cyan-400" />
                      <div>
                        <div className="text-xl font-bold text-white">{nodeWeather.wind_speed_kmh.toFixed(0)} km/h</div>
                        <div className="text-xs text-gray-400">Wind</div>
                      </div>
                    </div>
                  )}
                  {/* Precipitation */}
                  {nodeWeather.precipitation_mm !== null && nodeWeather.precipitation_mm > 0 && (
                    <div className="flex items-center gap-2">
                      <Droplets className="w-5 h-5 text-blue-400" />
                      <div>
                        <div className="text-xl font-bold text-white">{nodeWeather.precipitation_mm.toFixed(1)} mm</div>
                        <div className="text-xs text-gray-400">Precipitation</div>
                      </div>
                    </div>
                  )}
                  {/* Weather Impact */}
                  {nodeWeather.weather_impact !== null && nodeWeather.weather_impact > 0 && (
                    <div className="flex items-center gap-2">
                      <AlertTriangle className={`w-5 h-5 ${
                        nodeWeather.weather_impact >= 0.5 ? 'text-red-400' :
                        nodeWeather.weather_impact >= 0.3 ? 'text-orange-400' :
                        nodeWeather.weather_impact >= 0.1 ? 'text-yellow-400' :
                        'text-green-400'
                      }`} />
                      <div>
                        <div className={`text-xl font-bold ${
                          nodeWeather.weather_impact >= 0.5 ? 'text-red-400' :
                          nodeWeather.weather_impact >= 0.3 ? 'text-orange-400' :
                          nodeWeather.weather_impact >= 0.1 ? 'text-yellow-400' :
                          'text-green-400'
                        }`}>
                          {(nodeWeather.weather_impact * 100).toFixed(0)}%
                        </div>
                        <div className="text-xs text-gray-400">KPI Impact</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Executive Summary */}
          <div className="space-y-2">
            <SectionHeader
              title="Executive Summary"
              icon={<FileText className="w-5 h-5 text-blue-400" />}
              section="executive"
            />
            {expandedSections.has('executive') && (
              <div className="bg-gray-750 rounded-lg p-4 border border-gray-600 space-y-4">
                {/* Key Findings */}
                {report.executiveSummary.keyFindings.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
                      <Activity className="w-4 h-4 text-blue-400" />
                      Key Findings
                    </h4>
                    <ul className="space-y-1">
                      {report.executiveSummary.keyFindings.map((finding, i) => (
                        <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
                          <span className="text-blue-400 mt-0.5">•</span>
                          {toDisplayString(finding)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Urgent Issues */}
                {report.executiveSummary.urgentIssues.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-red-400 mb-2 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" />
                      Urgent Issues
                    </h4>
                    <ul className="space-y-1">
                      {report.executiveSummary.urgentIssues.map((issue, i) => (
                        <li key={i} className="text-sm text-red-300 flex items-start gap-2">
                          <span className="text-red-400 mt-0.5">!</span>
                          {toDisplayString(issue)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Recommendations */}
                {report.executiveSummary.recommendations.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-green-400 mb-2 flex items-center gap-2">
                      <Zap className="w-4 h-4" />
                      Recommendations
                    </h4>
                    <ul className="space-y-1">
                      {report.executiveSummary.recommendations.map((rec, i) => (
                        <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
                          <span className="text-green-400 mt-0.5">{i + 1}.</span>
                          {toDisplayString(rec)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Performance Analysis */}
          <div className="space-y-2">
            <SectionHeader
              title="Performance Analysis"
              icon={<BarChart2 className="w-5 h-5 text-green-400" />}
              section="performance"
              badge={report.rawDataSummary.kpiRecordsAnalyzed}
            />
            {expandedSections.has('performance') && (
              <div className="bg-gray-750 rounded-lg p-4 border border-gray-600 space-y-4">
                {report.performanceAnalysis.summary && (
                  <p className="text-sm text-gray-300">{toDisplayString(report.performanceAnalysis.summary)}</p>
                )}

                {/* KPI Trends */}
                <div className="grid grid-cols-2 gap-3">
                  {report.performanceAnalysis.kpiTrends.map((kpi, i) => (
                    <div key={i} className="bg-gray-700 rounded-lg p-3 border border-gray-600">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-gray-400">{kpi.metric}</span>
                        {getTrendIcon(kpi.trend)}
                      </div>
                      <div className="text-lg font-bold text-white">
                        {kpi.currentValue}
                      </div>
                      <div className="text-xs text-gray-500">
                        Avg: {kpi.avgValue} | Range: {kpi.minValue} - {kpi.maxValue}
                      </div>
                      {kpi.interpretation && (
                        <div className="text-xs text-gray-400 mt-2 italic">
                          {toDisplayString(kpi.interpretation)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Anomalies */}
                {report.performanceAnalysis.anomalies.length > 0 && (
                  <div className="bg-yellow-900/20 border border-yellow-700 rounded-lg p-3">
                    <h4 className="text-sm font-semibold text-yellow-400 mb-2">Detected Anomalies</h4>
                    <ul className="space-y-1">
                      {report.performanceAnalysis.anomalies.map((anomaly, i) => (
                        <li key={i} className="text-xs text-yellow-300">{toDisplayString(anomaly)}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {report.performanceAnalysis.comparisonToFleet && (
                  <div className="text-xs text-gray-400 italic">
                    <strong>Fleet Comparison:</strong> {toDisplayString(report.performanceAnalysis.comparisonToFleet)}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Equipment Status with Line Graphs */}
          <div className="space-y-2">
            <SectionHeader
              title="Equipment Status (7-Day Trends)"
              icon={<Server className="w-5 h-5 text-purple-400" />}
              section="equipment"
            />
            {expandedSections.has('equipment') && (
              <div className="bg-gray-750 rounded-lg p-4 border border-gray-600 space-y-4">
                {report.equipmentStatus.summary && (
                  <p className="text-sm text-gray-300">{toDisplayString(report.equipmentStatus.summary)}</p>
                )}

                {/* Equipment Line Graphs */}
                {equipmentHistory && equipmentHistory.history.length > 0 ? (
                  <div className="space-y-4">
                    {/* Row 1: AAU Temperature + BBU CPU */}
                    <div className="grid grid-cols-2 gap-4">
                      {/* AAU Temperature */}
                      <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Radio className="w-4 h-4 text-cyan-400" />
                            <span className="text-sm font-medium text-cyan-400">AAU Temperature</span>
                          </div>
                          <span className="text-lg font-bold text-white">
                            {equipmentHistory.statistics.aau.temperature.current.toFixed(1)}°C
                          </span>
                        </div>
                        <div className="h-16">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={equipmentHistory.history.slice().reverse()}>
                              <YAxis
                                hide
                                domain={[
                                  Math.min(...equipmentHistory.history.map(h => h.aau.avg_temperature_celsius)) - 5,
                                  Math.max(...equipmentHistory.history.map(h => h.aau.avg_temperature_celsius)) + 5
                                ]}
                              />
                              <XAxis hide dataKey="timestamp" />
                              <Tooltip
                                contentStyle={{ background: '#ffffff', border: '1px solid #E6E7EF', borderRadius: '4px' }}
                                labelFormatter={(_, payload) => payload?.[0]?.payload?.timestamp ? new Date(payload[0].payload.timestamp).toLocaleDateString() : ''}
                                formatter={(value: number) => [`${value.toFixed(1)}°C`, 'Temp']}
                              />
                              <Line
                                type="monotone"
                                dataKey="aau.avg_temperature_celsius"
                                stroke="#22d3ee"
                                strokeWidth={2}
                                dot={false}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                          <span>Min: {equipmentHistory.statistics.aau.temperature.min.toFixed(1)}°C</span>
                          <span>Avg: {equipmentHistory.statistics.aau.temperature.avg.toFixed(1)}°C</span>
                          <span>Max: {equipmentHistory.statistics.aau.temperature.max.toFixed(1)}°C</span>
                        </div>
                      </div>

                      {/* BBU CPU Utilization */}
                      <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Cpu className="w-4 h-4 text-purple-400" />
                            <span className="text-sm font-medium text-purple-400">BBU CPU Load</span>
                          </div>
                          <span className={`text-lg font-bold ${
                            equipmentHistory.statistics.bbu.cpu_utilization.current > 80 ? 'text-red-400' :
                            equipmentHistory.statistics.bbu.cpu_utilization.current > 60 ? 'text-yellow-400' : 'text-white'
                          }`}>
                            {equipmentHistory.statistics.bbu.cpu_utilization.current.toFixed(1)}%
                          </span>
                        </div>
                        <div className="h-16">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={equipmentHistory.history.slice().reverse()}>
                              <YAxis hide domain={[0, 100]} />
                              <XAxis hide dataKey="timestamp" />
                              <Tooltip
                                contentStyle={{ background: '#ffffff', border: '1px solid #E6E7EF', borderRadius: '4px' }}
                                labelFormatter={(_, payload) => payload?.[0]?.payload?.timestamp ? new Date(payload[0].payload.timestamp).toLocaleDateString() : ''}
                                formatter={(value: number) => [`${value.toFixed(1)}%`, 'CPU']}
                              />
                              <Line
                                type="monotone"
                                dataKey="bbu.cpu_utilization_percent"
                                stroke="#a855f7"
                                strokeWidth={2}
                                dot={false}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                          <span>Min: {equipmentHistory.statistics.bbu.cpu_utilization.min.toFixed(1)}%</span>
                          <span>Avg: {equipmentHistory.statistics.bbu.cpu_utilization.avg.toFixed(1)}%</span>
                          <span>Max: {equipmentHistory.statistics.bbu.cpu_utilization.max.toFixed(1)}%</span>
                        </div>
                      </div>
                    </div>

                    {/* Row 2: HVAC Temperature + Power Load */}
                    <div className="grid grid-cols-2 gap-4">
                      {/* HVAC Temperature */}
                      <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Fan className="w-4 h-4 text-blue-400" />
                            <span className="text-sm font-medium text-blue-400">HVAC Temperature</span>
                          </div>
                          <span className="text-lg font-bold text-white">
                            {equipmentHistory.statistics.hvac.temperature.current.toFixed(1)}°C
                          </span>
                        </div>
                        <div className="h-16">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={equipmentHistory.history.slice().reverse()}>
                              <YAxis
                                hide
                                domain={[
                                  Math.min(...equipmentHistory.history.map(h => h.hvac.current_temp_celsius)) - 2,
                                  Math.max(...equipmentHistory.history.map(h => h.hvac.current_temp_celsius)) + 2
                                ]}
                              />
                              <XAxis hide dataKey="timestamp" />
                              <Tooltip
                                contentStyle={{ background: '#ffffff', border: '1px solid #E6E7EF', borderRadius: '4px' }}
                                labelFormatter={(_, payload) => payload?.[0]?.payload?.timestamp ? new Date(payload[0].payload.timestamp).toLocaleDateString() : ''}
                                formatter={(value: number) => [`${value.toFixed(1)}°C`, 'Temp']}
                              />
                              <Line
                                type="monotone"
                                dataKey="hvac.current_temp_celsius"
                                stroke="#3b82f6"
                                strokeWidth={2}
                                dot={false}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                          <span>Min: {equipmentHistory.statistics.hvac.temperature.min.toFixed(1)}°C</span>
                          <span>Avg: {equipmentHistory.statistics.hvac.temperature.avg.toFixed(1)}°C</span>
                          <span>Max: {equipmentHistory.statistics.hvac.temperature.max.toFixed(1)}°C</span>
                        </div>
                      </div>

                      {/* Power Load */}
                      <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Zap className="w-4 h-4 text-yellow-400" />
                            <span className="text-sm font-medium text-yellow-400">Power Load</span>
                          </div>
                          <span className="text-lg font-bold text-white">
                            {equipmentHistory.statistics.power.load.current.toFixed(1)} kW
                          </span>
                        </div>
                        <div className="h-16">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={equipmentHistory.history.slice().reverse()}>
                              <YAxis
                                hide
                                domain={[
                                  0,
                                  Math.max(...equipmentHistory.history.map(h => h.power.current_load_kw)) * 1.2
                                ]}
                              />
                              <XAxis hide dataKey="timestamp" />
                              <Tooltip
                                contentStyle={{ background: '#ffffff', border: '1px solid #E6E7EF', borderRadius: '4px' }}
                                labelFormatter={(_, payload) => payload?.[0]?.payload?.timestamp ? new Date(payload[0].payload.timestamp).toLocaleDateString() : ''}
                                formatter={(value: number) => [`${value.toFixed(2)} kW`, 'Load']}
                              />
                              <Line
                                type="monotone"
                                dataKey="power.current_load_kw"
                                stroke="#facc15"
                                strokeWidth={2}
                                dot={false}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                          <span>Min: {equipmentHistory.statistics.power.load.min.toFixed(2)} kW</span>
                          <span>Avg: {equipmentHistory.statistics.power.load.avg.toFixed(2)} kW</span>
                          <span>Max: {equipmentHistory.statistics.power.load.max.toFixed(2)} kW</span>
                        </div>
                      </div>
                    </div>

                    {/* Row 3: UPS Battery Health */}
                    <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Battery className="w-4 h-4 text-green-400" />
                          <span className="text-sm font-medium text-green-400">UPS Battery Health</span>
                        </div>
                        <span className={`text-lg font-bold ${
                          equipmentHistory.statistics.power.battery_health.current >= 80 ? 'text-green-400' :
                          equipmentHistory.statistics.power.battery_health.current >= 50 ? 'text-yellow-400' : 'text-red-400'
                        }`}>
                          {equipmentHistory.statistics.power.battery_health.current.toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-12">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={equipmentHistory.history.slice().reverse()}>
                            <YAxis hide domain={[0, 100]} />
                            <XAxis hide dataKey="timestamp" />
                            <Tooltip
                              contentStyle={{ background: '#ffffff', border: '1px solid #E6E7EF', borderRadius: '4px' }}
                              labelFormatter={(_, payload) => payload?.[0]?.payload?.timestamp ? new Date(payload[0].payload.timestamp).toLocaleDateString() : ''}
                              formatter={(value: number) => [`${value.toFixed(1)}%`, 'Health']}
                            />
                            <Line
                              type="monotone"
                              dataKey="power.battery_health_percent"
                              stroke="#22c55e"
                              strokeWidth={2}
                              dot={false}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="flex justify-between text-xs text-gray-500 mt-1">
                        <span>Min: {equipmentHistory.statistics.power.battery_health.min.toFixed(1)}%</span>
                        <span>Avg: {equipmentHistory.statistics.power.battery_health.avg.toFixed(1)}%</span>
                        <span>Max: {equipmentHistory.statistics.power.battery_health.max.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                ) : equipmentHistory ? (
                  <div className="text-center py-4 text-gray-400">
                    <Activity className="w-6 h-6 mx-auto mb-2" />
                    <p className="text-sm">No equipment trend data available</p>
                  </div>
                ) : (
                  <div className="text-center py-4 text-gray-400">
                    <Activity className="w-6 h-6 mx-auto mb-2 animate-pulse" />
                    <p className="text-sm">Loading equipment trend data...</p>
                  </div>
                )}

                {/* Hardware/Firmware Status */}
                <div className="grid grid-cols-2 gap-4 pt-2 border-t border-gray-700">
                  <div>
                    <h4 className="text-xs font-semibold text-gray-400 mb-1">Hardware Health</h4>
                    <p className="text-sm text-gray-300">{toDisplayString(report.equipmentStatus.hardwareHealth) || 'Not assessed'}</p>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-gray-400 mb-1">Firmware Status</h4>
                    <p className="text-sm text-gray-300">{toDisplayString(report.equipmentStatus.firmwareStatus) || 'Not assessed'}</p>
                  </div>
                </div>

                {report.equipmentStatus.maintenanceNeeds.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-yellow-400 mb-1">Maintenance Needs</h4>
                    <ul className="space-y-1">
                      {report.equipmentStatus.maintenanceNeeds.map((need, i) => (
                        <li key={i} className="text-xs text-yellow-300 flex items-start gap-1">
                          <Wrench className="w-3 h-3 mt-0.5" />
                          {toDisplayString(need)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {report.equipmentStatus.endOfLifeWarnings.length > 0 && (
                  <div className="bg-red-900/20 border border-red-700 rounded p-2">
                    <h4 className="text-xs font-semibold text-red-400 mb-1">End of Life Warnings</h4>
                    <ul className="space-y-1">
                      {report.equipmentStatus.endOfLifeWarnings.map((warning, i) => (
                        <li key={i} className="text-xs text-red-300">{toDisplayString(warning)}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Alert Analysis */}
          <div className="space-y-2">
            <SectionHeader
              title="Alert Analysis"
              icon={<AlertTriangle className="w-5 h-5 text-orange-400" />}
              section="alerts"
              badge={report.alertAnalysis.totalAlerts}
            />
            {expandedSections.has('alerts') && (
              <div className="bg-gray-750 rounded-lg p-4 border border-gray-600 space-y-3">
                {/* Alert Stats */}
                <div className="grid grid-cols-4 gap-3 text-center">
                  <div className="bg-gray-700 rounded p-2">
                    <div className="text-lg font-bold text-white">{report.alertAnalysis.totalAlerts}</div>
                    <div className="text-xs text-gray-400">Total</div>
                  </div>
                  <div className="bg-gray-700 rounded p-2">
                    <div className="text-lg font-bold text-red-400">{report.alertAnalysis.criticalAlerts}</div>
                    <div className="text-xs text-gray-400">Critical</div>
                  </div>
                  <div className="bg-gray-700 rounded p-2">
                    <div className="text-lg font-bold text-yellow-400">{report.alertAnalysis.warningAlerts}</div>
                    <div className="text-xs text-gray-400">Warning</div>
                  </div>
                  <div className="bg-gray-700 rounded p-2">
                    <div className="text-lg font-bold text-green-400">{report.alertAnalysis.resolvedAlerts}</div>
                    <div className="text-xs text-gray-400">Resolved</div>
                  </div>
                </div>

                {/* Alert List - Actual alerts for drill-down */}
                {report.alertAnalysis.alertList && report.alertAnalysis.alertList.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-400 mb-2">Alert Details (Top {report.alertAnalysis.alertList.length})</h4>
                    <div className="max-h-64 overflow-y-auto space-y-2">
                      {report.alertAnalysis.alertList.filter(alert => alert && alert.alert_id).map((alert, i) => (
                        <div
                          key={alert.alert_id || i}
                          className={`p-2 rounded border ${
                            alert.severity === 'critical'
                              ? 'bg-red-900/30 border-red-700'
                              : alert.severity === 'warning'
                              ? 'bg-yellow-900/30 border-yellow-700'
                              : 'bg-blue-900/30 border-blue-700'
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className={`text-xs px-1.5 py-0.5 rounded uppercase font-medium ${
                                  alert.severity === 'critical'
                                    ? 'bg-red-800 text-red-200'
                                    : alert.severity === 'warning'
                                    ? 'bg-yellow-800 text-yellow-200'
                                    : 'bg-blue-800 text-blue-200'
                                }`}>
                                  {alert.severity || 'info'}
                                </span>
                                <span className="text-xs text-gray-400 capitalize">
                                  {(alert.alert_type || 'unknown').replace(/_/g, ' ')}
                                </span>
                                <span className={`text-xs px-1.5 py-0.5 rounded ${
                                  alert.status === 'active'
                                    ? 'bg-orange-800 text-orange-200'
                                    : 'bg-green-800 text-green-200'
                                }`}>
                                  {alert.status || 'unknown'}
                                </span>
                              </div>
                              <p className="text-xs text-gray-300 line-clamp-2">{alert.description || 'No description'}</p>
                            </div>
                            <div className="text-xs text-gray-500 whitespace-nowrap ml-2">
                              {toDateString(alert.timestamp)}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                    {report.alertAnalysis.totalAlerts > report.alertAnalysis.alertList.length && (
                      <p className="text-xs text-gray-500 mt-2 text-center">
                        Showing {report.alertAnalysis.alertList.length} of {report.alertAnalysis.totalAlerts} alerts
                      </p>
                    )}
                  </div>
                )}

                {/* Common Issues */}
                {report.alertAnalysis.commonIssues.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-400 mb-1">Common Issues</h4>
                    <ul className="space-y-1">
                      {report.alertAnalysis.commonIssues.map((issue, i) => (
                        <li key={i} className="text-xs text-gray-300">{toDisplayString(issue)}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {report.alertAnalysis.patternAnalysis && (
                  <div className="text-xs text-gray-400 italic">
                    <strong>Pattern Analysis:</strong> {toDisplayString(report.alertAnalysis.patternAnalysis)}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Remediation Analysis */}
          <div className="space-y-2">
            <SectionHeader
              title="Remediation Effectiveness"
              icon={<Wrench className="w-5 h-5 text-cyan-400" />}
              section="remediation"
              badge={report.remediationAnalysis.totalActions}
            />
            {expandedSections.has('remediation') && (
              <div className="bg-gray-750 rounded-lg p-4 border border-gray-600 space-y-3">
                {/* Stats */}
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="bg-gray-700 rounded p-2">
                    <div className="text-lg font-bold text-blue-400">
                      {safeNumber(report.remediationAnalysis.successRate, 0, '0')}%
                    </div>
                    <div className="text-xs text-gray-400">Success Rate</div>
                  </div>
                  <div className="bg-gray-700 rounded p-2">
                    <div className="text-lg font-bold text-green-400">
                      {report.remediationAnalysis.avgResolutionTime || 'N/A'}
                    </div>
                    <div className="text-xs text-gray-400">Avg Resolution</div>
                  </div>
                  <div className="bg-gray-700 rounded p-2">
                    <div className="text-lg font-bold text-red-400">
                      {report.remediationAnalysis.failedActions ?? 0}
                    </div>
                    <div className="text-xs text-gray-400">Failed Actions</div>
                  </div>
                </div>

                {/* Most Effective Actions */}
                {report.remediationAnalysis.mostEffectiveActions.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-green-400 mb-1">Most Effective Actions</h4>
                    <ul className="space-y-1">
                      {report.remediationAnalysis.mostEffectiveActions.map((action, i) => (
                        <li key={i} className="text-xs text-green-300 flex items-start gap-1">
                          <CheckCircle2 className="w-3 h-3 mt-0.5" />
                          {toDisplayString(action)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Improvement Suggestions */}
                {report.remediationAnalysis.improvementSuggestions.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-blue-400 mb-1">Improvement Suggestions</h4>
                    <ul className="space-y-1">
                      {report.remediationAnalysis.improvementSuggestions.map((sug, i) => (
                        <li key={i} className="text-xs text-blue-300">{toDisplayString(sug)}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Predictive Insights */}
          <div className="space-y-2">
            <SectionHeader
              title="Predictive Insights"
              icon={<Shield className="w-5 h-5 text-indigo-400" />}
              section="predictive"
            />
            {expandedSections.has('predictive') && (
              <div className="bg-gray-750 rounded-lg p-4 border border-gray-600 space-y-3">
                {/* Risk Score */}
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <div className={`text-3xl font-bold ${getRiskColor(report.predictiveInsights.riskScore)}`}>
                      {report.predictiveInsights.riskScore}
                    </div>
                    <div className="text-xs text-gray-400">Risk Score</div>
                  </div>
                  <div className="flex-1">
                    <div className="w-full bg-gray-700 rounded-full h-3">
                      <div
                        className={`h-3 rounded-full transition-all ${
                          report.predictiveInsights.riskScore >= 70 ? 'bg-red-500' :
                          report.predictiveInsights.riskScore >= 40 ? 'bg-yellow-500' :
                          'bg-green-500'
                        }`}
                        style={{ width: `${report.predictiveInsights.riskScore}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>Low Risk</span>
                      <span>High Risk</span>
                    </div>
                  </div>
                </div>

                {/* Potential Issues */}
                {report.predictiveInsights.potentialIssues.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-yellow-400 mb-1">Potential Issues</h4>
                    <ul className="space-y-1">
                      {report.predictiveInsights.potentialIssues.map((issue, i) => (
                        <li key={i} className="text-xs text-yellow-300 flex items-start gap-1">
                          <AlertTriangle className="w-3 h-3 mt-0.5" />
                          {toDisplayString(issue)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Maintenance Recommendations */}
                {report.predictiveInsights.maintenanceRecommendations.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-blue-400 mb-1 flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      Maintenance Recommendations
                    </h4>
                    <ul className="space-y-1">
                      {report.predictiveInsights.maintenanceRecommendations.map((rec, i) => (
                        <li key={i} className="text-xs text-blue-300">{toDisplayString(rec)}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Capacity Forecast */}
                {report.predictiveInsights.capacityForecast && (
                  <div className="text-xs text-gray-400 italic">
                    <strong>Capacity Forecast:</strong> {toDisplayString(report.predictiveInsights.capacityForecast)}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Report Metadata */}
          <div className="text-xs text-gray-500 flex items-center justify-between pt-4 border-t border-gray-700">
            <div className="flex items-center gap-4">
              <span>Generated: {toDateString(report.generatedAt)}</span>
              <span>KPIs: {report.rawDataSummary.kpiRecordsAnalyzed}</span>
              <span>Alerts: {report.rawDataSummary.alertsAnalyzed}</span>
              <span>Actions: {report.rawDataSummary.actionsAnalyzed}</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>
                Data range: {toDateString(report.rawDataSummary.timeRangeStart).split(',')[0]} -{' '}
                {toDateString(report.rawDataSummary.timeRangeEnd).split(',')[0]}
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-800 px-6 py-4 border-t border-gray-700">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Close Report
          </button>
        </div>
      </div>
    </div>
  );
});

NodeStatusReportModal.displayName = 'NodeStatusReportModal';

export default NodeStatusReportModal;
