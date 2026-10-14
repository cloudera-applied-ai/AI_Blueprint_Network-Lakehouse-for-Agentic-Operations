/**
 * Node Analysis Service - AI-powered node status analysis and reporting
 * Uses LLM to generate comprehensive status reports with performance interpretation
 */

import { llmService } from './llmService';
import { LLMMessage } from '@/types/llm';
import {
  FiberNode,
  KPIMetrics,
  Alert,
  SelfHealingAction,
} from '@/types';
import {
  getAllSensorData,
  insertAntennaSensors,
  insertWeatherData,
  insertEnvSensors,
  insertEquipmentSensors,
} from './memoryStore';
import { generateAllSensorData } from './sensorDataGenerator';
import { apiClient, getKPIs, getAlerts, getActions } from './apiClient';

// Equipment API response types
interface EquipmentSummary {
  overall_health: string;
  aau_status: string;
  bbu_status: string;
  hvac_status: string;
  power_status: string;
  total_aau: number;
}

interface EquipmentAPIResponse {
  node_id: string;
  aau_units: Array<{
    aau_id: string;
    status: string;
    temperature_celsius: number;
    efficiency_percent: number;
  }>;
  bbu: {
    status: string;
    cpu_utilization_percent: number;
    memory_utilization_percent: number;
    temperature_celsius: number;
  };
  hvac: {
    status: string;
    current_temp_celsius: number;
    setpoint_celsius: number;
    compressor_status: string;
    high_temp_alarm: boolean;
  };
  power: {
    grid_status: string;
    battery_health_percent: number;
    battery_backup_hours: number;
    ups_status: string;
    current_load_kw: number;
    max_load_kw: number;
  };
  summary: EquipmentSummary;
}

/**
 * Helper to safely convert a date value (string or Date) to Date object
 */
const toDate = (value: Date | string | undefined | null): Date => {
  if (!value) return new Date();
  if (value instanceof Date) return value;
  const parsed = new Date(value);
  return isNaN(parsed.getTime()) ? new Date() : parsed;
};

/**
 * Node Analysis Report structure
 */
export interface NodeAnalysisReport {
  nodeId: string;
  nodeName: string;
  generatedAt: Date;
  analysisStatus: 'generating' | 'complete' | 'error';
  error?: string;

  // Executive Summary
  executiveSummary: {
    overallHealth: 'excellent' | 'good' | 'fair' | 'poor' | 'critical';
    healthScore: number; // 0-100
    keyFindings: string[];
    urgentIssues: string[];
    recommendations: string[];
  };

  // Performance Analysis
  performanceAnalysis: {
    summary: string;
    kpiTrends: {
      metric: string;
      trend: 'improving' | 'stable' | 'declining';
      currentValue: number;
      avgValue: number;
      minValue: number;
      maxValue: number;
      interpretation: string;
    }[];
    anomalies: string[];
    comparisonToFleet: string;
  };

  // Equipment Status
  equipmentStatus: {
    summary: string;
    hardwareHealth: string;
    firmwareStatus: string;
    maintenanceNeeds: string[];
    endOfLifeWarnings: string[];
  };

  // Alert History Analysis
  alertAnalysis: {
    totalAlerts: number;
    criticalAlerts: number;
    warningAlerts: number;
    resolvedAlerts: number;
    activeAlerts: number;
    commonIssues: string[];
    patternAnalysis: string;
    // Actual alert list for drill-down
    alertList: {
      alert_id: string;
      alert_type: string;
      severity: 'critical' | 'warning' | 'info';
      status: string;
      description: string;
      timestamp: Date;
    }[];
  };

  // Remediation Effectiveness
  remediationAnalysis: {
    totalActions: number;
    successRate: number;
    avgResolutionTime: string;
    mostEffectiveActions: string[];
    failedActions: number;
    improvementSuggestions: string[];
  };

  // Predictive Insights
  predictiveInsights: {
    riskScore: number; // 0-100
    potentialIssues: string[];
    maintenanceRecommendations: string[];
    capacityForecast: string;
  };

  // Raw Data Summary (for debugging/verification)
  rawDataSummary: {
    kpiRecordsAnalyzed: number;
    alertsAnalyzed: number;
    actionsAnalyzed: number;
    timeRangeStart: Date;
    timeRangeEnd: Date;
  };
}

/**
 * Analysis Agent types for modular analysis
 */
type AnalysisAgent = 'performance' | 'equipment' | 'alerts' | 'remediation' | 'predictive';

class NodeAnalysisService {
  /**
   * Generate a comprehensive AI-powered status report for a node
   */
  async generateNodeReport(
    node: FiberNode,
    onProgress?: (stage: string, progress: number) => void
  ): Promise<NodeAnalysisReport> {
    const startTime = Date.now();

    // Initialize report structure
    const report: NodeAnalysisReport = {
      nodeId: node.node_id,
      nodeName: `${node.city} - ${node.node_id}`,
      generatedAt: new Date(),
      analysisStatus: 'generating',
      executiveSummary: {
        overallHealth: 'good',
        healthScore: 0,
        keyFindings: [],
        urgentIssues: [],
        recommendations: [],
      },
      performanceAnalysis: {
        summary: '',
        kpiTrends: [],
        anomalies: [],
        comparisonToFleet: '',
      },
      equipmentStatus: {
        summary: '',
        hardwareHealth: '',
        firmwareStatus: '',
        maintenanceNeeds: [],
        endOfLifeWarnings: [],
      },
      alertAnalysis: {
        totalAlerts: 0,
        criticalAlerts: 0,
        warningAlerts: 0,
        resolvedAlerts: 0,
        activeAlerts: 0,
        commonIssues: [],
        patternAnalysis: '',
        alertList: [],
      },
      remediationAnalysis: {
        totalActions: 0,
        successRate: 0,
        avgResolutionTime: '',
        mostEffectiveActions: [],
        failedActions: 0,
        improvementSuggestions: [],
      },
      predictiveInsights: {
        riskScore: 0,
        potentialIssues: [],
        maintenanceRecommendations: [],
        capacityForecast: '',
      },
      rawDataSummary: {
        kpiRecordsAnalyzed: 0,
        alertsAnalyzed: 0,
        actionsAnalyzed: 0,
        timeRangeStart: new Date(),
        timeRangeEnd: new Date(),
      },
    };

    try {
      // Stage 1: Gather data directly from backend API
      onProgress?.('Gathering node data from backend...', 10);

      // Get last 60 days of data
      const sixtyDaysAgo = new Date();
      sixtyDaysAgo.setDate(sixtyDaysAgo.getDate() - 60);
      const startTimeISO = sixtyDaysAgo.toISOString();

      // Fetch data directly from backend API (not memoryStore which only has 1 day)
      // Note: Backend KPI endpoint has max limit of 1000 records
      const [kpisResponse, alertsResponse, actionsResponse] = await Promise.all([
        getKPIs({ node_id: node.node_id, limit: 1000, start_time: startTimeISO }),
        getAlerts({ node_id: node.node_id, limit: 1000, start_time: startTimeISO }),
        getActions({ node_id: node.node_id, limit: 500 }),
      ]);

      // Convert API responses to typed objects with Date timestamps
      const kpis: KPIMetrics[] = (kpisResponse.items || []).map((item: Record<string, unknown>) => ({
        ...item,
        timestamp: toDate(item.timestamp as string),
      })) as unknown as KPIMetrics[];

      const alerts: Alert[] = (alertsResponse.items || []).map((item: Record<string, unknown>) => ({
        ...item,
        // Normalize API fields to frontend format
        alert_type: (item.type as string || item.alert_type as string || 'unknown'),
        severity: (item.severity as string || 'info').toLowerCase() as Alert['severity'],
        status: (item.status as string || 'active').toLowerCase() as Alert['status'],
        timestamp: toDate(item.timestamp as string),
        resolved_at: item.resolved_at ? toDate(item.resolved_at as string) : undefined,
      })) as unknown as Alert[];

      const actions: SelfHealingAction[] = (actionsResponse.items || []).map((item: Record<string, unknown>) => ({
        ...item,
        // Normalize API fields to frontend format
        status: (item.status as string || 'pending').toLowerCase() as SelfHealingAction['status'],
        action_type: (item.action_type as string || 'unknown').toLowerCase() as SelfHealingAction['action_type'],
        // API uses start_time/end_time, frontend uses timestamp/completion_time
        timestamp: toDate(item.start_time as string || item.timestamp as string),
        completion_time: item.end_time ? toDate(item.end_time as string) :
                        item.completed_at ? toDate(item.completed_at as string) : undefined,
      })) as unknown as SelfHealingAction[];

      console.log(`[NodeAnalysis] Fetched from backend for ${node.node_id} - KPIs: ${kpis.length}, Alerts: ${alerts.length}, Actions: ${actions.length}`);
      if (alerts.length > 0) {
        console.log(`[NodeAnalysis] First alert: severity=${alerts[0].severity}, status=${alerts[0].status}, type=${alerts[0].alert_type}`);
        // Debug: Count alerts by severity/status before classification
        const criticalCount = alerts.filter(a => a.severity === 'critical').length;
        const warningCount = alerts.filter(a => a.severity === 'warning').length;
        const infoCount = alerts.filter(a => a.severity === 'info').length;
        const activeCount = alerts.filter(a => a.status === 'active').length;
        const resolvedCount = alerts.filter(a => a.status === 'resolved').length;
        console.log(`[NodeAnalysis] Alert breakdown: ${criticalCount} critical, ${warningCount} warning, ${infoCount} info, ${activeCount} active, ${resolvedCount} resolved`);
        // Show raw severity values for debugging
        const uniqueSeverities = [...new Set(alerts.map(a => a.severity))];
        const uniqueStatuses = [...new Set(alerts.map(a => a.status))];
        console.log(`[NodeAnalysis] Unique severities: ${JSON.stringify(uniqueSeverities)}, Unique statuses: ${JSON.stringify(uniqueStatuses)}`);
      }
      if (actions.length > 0) {
        console.log(`[NodeAnalysis] First action: status=${actions[0].status}, type=${actions[0].action_type}`);
      }

      // Update raw data summary with actual data range
      report.rawDataSummary = {
        kpiRecordsAnalyzed: kpis.length,
        alertsAnalyzed: alerts.length,
        actionsAnalyzed: actions.length,
        timeRangeStart: kpis.length > 0 ? kpis[0].timestamp : sixtyDaysAgo,
        timeRangeEnd: kpis.length > 0 ? kpis[kpis.length - 1].timestamp : new Date(),
      };

      // Stage 2: Calculate basic statistics
      onProgress?.('Analyzing performance metrics...', 25);
      this.calculateBasicStats(report, node, kpis, alerts, actions);
      console.log(`[NodeAnalysis] After calculateBasicStats - alertAnalysis: total=${report.alertAnalysis.totalAlerts}, critical=${report.alertAnalysis.criticalAlerts}, warning=${report.alertAnalysis.warningAlerts}, active=${report.alertAnalysis.activeAlerts}, resolved=${report.alertAnalysis.resolvedAlerts}`);

      // Stage 2.5: Populate equipment status from sensor data (always do this)
      this.populateEquipmentFromSensors(report, node);

      // Stage 3: LLM Analysis (if available)
      if (llmService.isEnabled()) {
        onProgress?.('Generating AI insights...', 40);

        // Run analysis agents in parallel for speed
        const analysisPromises = [
          this.runAnalysisAgent('performance', node, kpis, alerts, actions),
          this.runAnalysisAgent('equipment', node, kpis, alerts, actions),
          this.runAnalysisAgent('alerts', node, kpis, alerts, actions),
          this.runAnalysisAgent('remediation', node, kpis, alerts, actions),
          this.runAnalysisAgent('predictive', node, kpis, alerts, actions),
        ];

        onProgress?.('Running AI analysis agents...', 60);

        const results = await Promise.allSettled(analysisPromises);

        // Process results from each agent
        results.forEach((result, index) => {
          if (result.status === 'fulfilled' && result.value) {
            const agentType = (['performance', 'equipment', 'alerts', 'remediation', 'predictive'] as AnalysisAgent[])[index];
            this.applyAgentResults(report, agentType, result.value);
          }
        });

        onProgress?.('Generating executive summary...', 85);

        // Generate executive summary using all data
        await this.generateExecutiveSummary(report, node, kpis, alerts, actions);

        // Fill in any gaps where LLM agents failed with rule-based fallbacks
        this.fillPredictiveInsightsFallback(report, node, kpis, alerts, actions);
      } else {
        // Fallback: Rule-based analysis without LLM
        onProgress?.('Generating rule-based analysis...', 60);
        await this.generateRuleBasedAnalysis(report, node, kpis, alerts, actions);
      }

      // Final stage
      onProgress?.('Finalizing report...', 95);
      report.analysisStatus = 'complete';

      console.log(`Node analysis completed in ${Date.now() - startTime}ms`);
      onProgress?.('Complete', 100);

      return report;

    } catch (error) {
      console.error('Node analysis error:', error);
      report.analysisStatus = 'error';
      report.error = error instanceof Error ? error.message : 'Unknown error during analysis';
      return report;
    }
  }

  /**
   * Calculate basic statistics from raw data
   */
  private calculateBasicStats(
    report: NodeAnalysisReport,
    node: FiberNode,
    kpis: KPIMetrics[],
    alerts: Alert[],
    actions: SelfHealingAction[]
  ): void {
    // Helper to determine if an alert is truly active
    // Must check BOTH status AND resolved_at due to known data inconsistency
    // where alerts can have status='active' but also have resolved_at set
    const isAlertTrulyActive = (a: Alert) => a.status === 'active' && !a.resolved_at;
    const isAlertResolved = (a: Alert) => a.status === 'resolved' || !!a.resolved_at;

    // Alert statistics
    report.alertAnalysis.totalAlerts = alerts.length;
    report.alertAnalysis.criticalAlerts = alerts.filter(a => a.severity === 'critical').length;
    report.alertAnalysis.warningAlerts = alerts.filter(a => a.severity === 'warning').length;
    report.alertAnalysis.activeAlerts = alerts.filter(isAlertTrulyActive).length;
    report.alertAnalysis.resolvedAlerts = alerts.filter(isAlertResolved).length;

    // Populate actual alert list (sorted by severity then timestamp, limit to 50 most recent)
    report.alertAnalysis.alertList = alerts
      .sort((a, b) => {
        const severityOrder = { critical: 0, warning: 1, info: 2 };
        const severityDiff = severityOrder[a.severity] - severityOrder[b.severity];
        if (severityDiff !== 0) return severityDiff;
        return b.timestamp.getTime() - a.timestamp.getTime();
      })
      .slice(0, 50)
      .map(alert => ({
        alert_id: alert.alert_id,
        alert_type: alert.alert_type,
        severity: alert.severity,
        status: alert.status,
        description: alert.description,
        timestamp: alert.timestamp,
      }));

    // Remediation statistics
    report.remediationAnalysis.totalActions = actions.length;
    const completedActions = actions.filter(a => a.status === 'completed');
    const failedActions = actions.filter(a => a.status === 'failed');
    report.remediationAnalysis.failedActions = failedActions.length;
    report.remediationAnalysis.successRate = actions.length > 0
      ? (completedActions.length / actions.length) * 100
      : 100;

    // Calculate average resolution time
    if (completedActions.length > 0) {
      const totalTime = completedActions.reduce((sum, action) => {
        if (action.completion_time) {
          return sum + (action.completion_time.getTime() - action.timestamp.getTime());
        }
        return sum;
      }, 0);
      const avgTimeMs = totalTime / completedActions.length;
      report.remediationAnalysis.avgResolutionTime = this.formatDuration(avgTimeMs);
    } else {
      report.remediationAnalysis.avgResolutionTime = 'N/A';
    }

    // KPI statistics
    if (kpis.length > 0) {
      const kpiMetrics = [
        { name: 'DS SNR', key: 'ds_snr_db', unit: 'dB' },
        { name: 'Packet Loss', key: 'packet_loss_percent', unit: '%' },
        { name: 'US SNR', key: 'us_snr_db', unit: 'dB' },
        { name: 'Downstream Throughput', key: 'downstream_throughput_mbps', unit: 'Mbps' },
        { name: 'Latency', key: 'latency_ms', unit: 'ms' },
        { name: 'Active Modems', key: 'active_modems', unit: '' },
      ];

      kpiMetrics.forEach(metric => {
        const rawValues = kpis.map(k => (k as unknown as Record<string, number>)[metric.key]);
        // Filter out undefined, null, and NaN values
        const values = rawValues.filter(v => v !== undefined && v !== null && !isNaN(v));

        if (values.length === 0) {
          // Skip this metric if no valid values
          return;
        }

        const avg = values.reduce((a, b) => a + b, 0) / values.length;
        const min = Math.min(...values);
        const max = Math.max(...values);
        const current = values[values.length - 1];

        // Calculate trend
        const recentValues = values.slice(-10);
        const olderValues = values.slice(-20, -10);
        const recentAvg = recentValues.length > 0 ? recentValues.reduce((a, b) => a + b, 0) / recentValues.length : avg;
        const olderAvg = olderValues.length > 0 ? olderValues.reduce((a, b) => a + b, 0) / olderValues.length : avg;

        let trend: 'improving' | 'stable' | 'declining' = 'stable';
        const changePct = ((recentAvg - olderAvg) / olderAvg) * 100;

        // For metrics where higher is better
        if (['ds_snr_db', 'us_snr_db', 'downstream_throughput_mbps'].includes(metric.key)) {
          if (changePct > 2) trend = 'improving';
          else if (changePct < -2) trend = 'declining';
        }
        // For metrics where lower is better
        else if (['packet_loss_percent', 'latency_ms'].includes(metric.key)) {
          if (changePct > 2) trend = 'declining';
          else if (changePct < -2) trend = 'improving';
        }

        report.performanceAnalysis.kpiTrends.push({
          metric: metric.name,
          trend,
          currentValue: Math.round(current * 100) / 100,
          avgValue: Math.round(avg * 100) / 100,
          minValue: Math.round(min * 100) / 100,
          maxValue: Math.round(max * 100) / 100,
          interpretation: '', // Will be filled by LLM or rule-based
        });
      });
    }

    // Calculate health score based on node status and TRULY ACTIVE alerts only
    // Note: Must check BOTH status='active' AND resolved_at=null due to data inconsistency
    // where alerts can have status='active' but also have resolved_at set
    const activeCriticalAlerts = alerts.filter(a => isAlertTrulyActive(a) && a.severity === 'critical').length;
    const activeWarningAlerts = alerts.filter(a => isAlertTrulyActive(a) && a.severity === 'warning').length;

    let healthScore = 100;
    if (node.status === 'degraded') healthScore -= 30;
    if (node.status === 'outage') healthScore -= 60;
    // Penalize for active alerts by severity (critical = 15, warning = 5)
    healthScore -= activeCriticalAlerts * 15;
    healthScore -= activeWarningAlerts * 5;
    healthScore = Math.max(0, Math.min(100, healthScore));

    report.executiveSummary.healthScore = healthScore;
    report.executiveSummary.overallHealth =
      healthScore >= 90 ? 'excellent' :
      healthScore >= 75 ? 'good' :
      healthScore >= 50 ? 'fair' :
      healthScore >= 25 ? 'poor' : 'critical';
  }

  /**
   * Run an analysis agent
   */
  private async runAnalysisAgent(
    agentType: AnalysisAgent,
    node: FiberNode,
    kpis: KPIMetrics[],
    alerts: Alert[],
    actions: SelfHealingAction[]
  ): Promise<Record<string, unknown> | null> {
    const prompt = this.buildAgentPrompt(agentType, node, kpis, alerts, actions);

    const messages: LLMMessage[] = [
      {
        role: 'system',
        content: this.getAgentSystemPrompt(agentType),
      },
      {
        role: 'user',
        content: prompt,
      },
    ];

    const response = await llmService.complete(messages);
    if (!response) return null;

    try {
      const jsonMatch = response.content.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]);
      }
    } catch (e) {
      console.error(`Failed to parse ${agentType} agent response:`, e);
    }

    return null;
  }

  /**
   * Get system prompt for each agent type
   */
  private getAgentSystemPrompt(agentType: AnalysisAgent): string {
    const prompts: Record<AnalysisAgent, string> = {
      performance: `You are an expert cable/ISP network performance analyst.
Analyze KPI metrics and provide insights on network performance.
Focus on SNR levels, throughput, latency, and modem counts.
Identify trends, anomalies, and areas needing attention.
Respond ONLY with valid JSON.`,

      equipment: `You are an expert cable/ISP equipment analyst.
Analyze equipment status including hardware, firmware, and maintenance needs.
Assess equipment health, predict potential failures, and recommend maintenance.
Consider manufacturer specifications and industry best practices.
Respond ONLY with valid JSON.`,

      alerts: `You are an expert cable/ISP alert and incident analyst.
Analyze alert patterns, identify common issues, and assess severity.
Look for recurring problems, temporal patterns, and root causes.
Recommend preventive measures based on alert history.
Respond ONLY with valid JSON.`,

      remediation: `You are an expert in cable/ISP self-healing and remediation systems.
Analyze remediation action effectiveness and success rates.
Identify which actions work best for different issues.
Recommend improvements to automated healing strategies.
Respond ONLY with valid JSON.`,

      predictive: `You are an expert in predictive analytics for cable/ISP networks.
Analyze trends to predict future issues and maintenance needs.
Assess risk levels and capacity requirements.
Provide actionable recommendations for proactive maintenance.
Respond ONLY with valid JSON.`,
    };

    return prompts[agentType];
  }

  /**
   * Build prompt for each agent type
   */
  private buildAgentPrompt(
    agentType: AnalysisAgent,
    node: FiberNode,
    kpis: KPIMetrics[],
    alerts: Alert[],
    actions: SelfHealingAction[]
  ): string {
    const nodeInfo = `
Node: ${node.node_id}
Location: ${node.city}, ${node.region}
Status: ${node.status}
Manufacturer: ${node.manufacturer}
Model: ${node.hardware_model}
Firmware: ${node.firmware_version}
DOCSIS Version: ${node.docsis_version || 'N/A'}
Node Type: ${node.node_type || 'N/A'}
Homes Active: ${node.homes_active || 'N/A'}
Last Maintenance: ${toDate(node.last_maintenance).toISOString()}
Next Maintenance: ${new Date(toDate(node.last_maintenance).getTime() + 90 * 24 * 60 * 60 * 1000).toISOString()}
`;

    switch (agentType) {
      case 'performance':
        return this.buildPerformancePrompt(nodeInfo, kpis);
      case 'equipment':
        return this.buildEquipmentPrompt(nodeInfo, node);
      case 'alerts':
        return this.buildAlertsPrompt(nodeInfo, alerts);
      case 'remediation':
        return this.buildRemediationPrompt(nodeInfo, actions);
      case 'predictive':
        return this.buildPredictivePrompt(nodeInfo, node, kpis, alerts, actions);
      default:
        return '';
    }
  }

  private buildPerformancePrompt(nodeInfo: string, kpis: KPIMetrics[]): string {
    // Sample KPIs for analysis (take first, middle, last 10)
    const sampleKpis = [
      ...kpis.slice(0, 10),
      ...kpis.slice(Math.floor(kpis.length / 2) - 5, Math.floor(kpis.length / 2) + 5),
      ...kpis.slice(-10),
    ];

    const kpiSummary = sampleKpis.map(k => ({
      ts: k.timestamp,
      ds_snr: k.ds_snr_db.toFixed(1),
      pkt_loss: k.packet_loss_percent.toFixed(2),
      us_snr: k.us_snr_db.toFixed(1),
      dl: k.downstream_throughput_mbps.toFixed(1),
      lat: k.latency_ms.toFixed(0),
      modems: k.active_modems,
    }));

    return `Analyze the performance metrics for this node:

${nodeInfo}

KPI Data Sample (${kpis.length} total records):
${JSON.stringify(kpiSummary.slice(0, 15), null, 2)}

IMPORTANT - Metric interpretation guidelines:
- HIGHER is better: ds_snr_db, us_snr_db, throughput
- LOWER is better: packet_loss_percent (less loss = good), latency (faster response = good)

Provide analysis in this JSON format:
{
  "summary": "Overall performance summary",
  "anomalies": ["List of detected anomalies"],
  "comparisonToFleet": "How does this compare to typical node performance",
  "interpretations": {
    "ds_snr_db": "Interpretation of this metric",
    "packet_loss_percent": "Interpretation (remember: LOWER is better)",
    "us_snr_db": "Interpretation",
    "throughput": "Interpretation",
    "latency": "Interpretation (remember: LOWER is better)"
  }
}`;
  }

  private buildEquipmentPrompt(nodeInfo: string, node: FiberNode): string {
    return `Analyze the equipment status for this node:

${nodeInfo}

Equipment Details:
- Hardware Model: ${node.hardware_model || 'N/A'}
- Firmware Version: ${node.firmware_version || 'N/A'}
- DOCSIS Version: ${node.docsis_version || 'N/A'}
- Node Type: ${node.node_type || 'N/A'}
- Downstream Channels: ${node.downstream_channels || 'N/A'}
- Upstream Channels: ${node.upstream_channels || 'N/A'}
- Power Supply Status: ${node.power_supply_status || 'N/A'}
- Battery Backup: ${node.battery_backup_hours || 'N/A'} hours
- Amplifier Cascade: ${node.amplifier_cascade || 'N/A'}
- Homes Passed: ${node.homes_passed || 'N/A'}
- Homes Active: ${node.homes_active || 'N/A'}

Provide analysis in this JSON format:
{
  "summary": "Overall equipment health summary",
  "hardwareHealth": "Assessment of hardware condition",
  "firmwareStatus": "Assessment of firmware/software versions",
  "maintenanceNeeds": ["List of maintenance recommendations"],
  "endOfLifeWarnings": ["Any end-of-life concerns"]
}`;
  }

  private buildAlertsPrompt(nodeInfo: string, alerts: Alert[]): string {
    const alertSummary = alerts.slice(-50).map(a => ({
      type: a.alert_type,
      severity: a.severity,
      status: a.status,
      desc: a.description.slice(0, 100),
      ts: a.timestamp,
    }));

    const alertsByType = alerts.reduce((acc, a) => {
      acc[a.alert_type] = (acc[a.alert_type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return `Analyze the alert history for this node:

${nodeInfo}

Total Alerts: ${alerts.length}
Alerts by Type: ${JSON.stringify(alertsByType)}
Critical: ${alerts.filter(a => a.severity === 'critical').length}
Warning: ${alerts.filter(a => a.severity === 'warning').length}
Active: ${alerts.filter(a => a.status === 'active').length}
Resolved: ${alerts.filter(a => a.status === 'resolved').length}

Recent Alerts:
${JSON.stringify(alertSummary.slice(-20), null, 2)}

Provide analysis in this JSON format:
{
  "commonIssues": ["List of common/recurring issues"],
  "patternAnalysis": "Analysis of alert patterns and root causes"
}`;
  }

  private buildRemediationPrompt(nodeInfo: string, actions: SelfHealingAction[]): string {
    const actionsByType = actions.reduce((acc, a) => {
      if (!acc[a.action_type]) {
        acc[a.action_type] = { total: 0, completed: 0, failed: 0 };
      }
      acc[a.action_type].total++;
      if (a.status === 'completed') acc[a.action_type].completed++;
      if (a.status === 'failed') acc[a.action_type].failed++;
      return acc;
    }, {} as Record<string, { total: number; completed: number; failed: number }>);

    return `Analyze the remediation history for this node:

${nodeInfo}

Total Actions: ${actions.length}
Completed: ${actions.filter(a => a.status === 'completed').length}
Failed: ${actions.filter(a => a.status === 'failed').length}

Actions by Type:
${JSON.stringify(actionsByType, null, 2)}

Provide analysis in this JSON format:
{
  "mostEffectiveActions": ["List of most effective action types"],
  "improvementSuggestions": ["Suggestions to improve remediation effectiveness"]
}`;
  }

  private buildPredictivePrompt(
    nodeInfo: string,
    node: FiberNode,
    kpis: KPIMetrics[],
    alerts: Alert[],
    actions: SelfHealingAction[]
  ): string {
    // Calculate trends for prediction
    const recentKpis = kpis.slice(-100);
    const avgMetrics = recentKpis.length > 0 ? {
      ds_snr: recentKpis.reduce((s, k) => s + k.ds_snr_db, 0) / recentKpis.length,
      pkt_loss: recentKpis.reduce((s, k) => s + k.packet_loss_percent, 0) / recentKpis.length,
      modems: recentKpis.reduce((s, k) => s + k.active_modems, 0) / recentKpis.length,
    } : { ds_snr: 0, pkt_loss: 0, modems: 0 };

    const daysSinceLastMaintenance = Math.floor(
      (Date.now() - toDate(node.last_maintenance).getTime()) / (1000 * 60 * 60 * 24)
    );

    const homesActive = node.homes_active || 350;
    const homesPassed = node.homes_passed || 500;

    return `Provide predictive analysis for this node:

${nodeInfo}

Current Metrics (Avg of last 100 samples):
- DS SNR: ${avgMetrics.ds_snr.toFixed(1)} dB
- Packet Loss: ${avgMetrics.pkt_loss.toFixed(2)}%
- Active Modems: ${avgMetrics.modems.toFixed(0)}
- Homes Passed: ${homesPassed}
- Homes Active: ${homesActive}
- Utilization: ${((homesActive / homesPassed) * 100).toFixed(1)}%

Maintenance Status:
- Days since last maintenance: ${daysSinceLastMaintenance}

Recent Alert Trend: ${alerts.filter(a => {
  const dayAgo = Date.now() - 24 * 60 * 60 * 1000;
  return a.timestamp.getTime() > dayAgo;
}).length} alerts in last 24h

Failed Actions: ${actions.filter(a => a.status === 'failed').length}

Provide analysis in this JSON format:
{
  "riskScore": 0-100,
  "potentialIssues": ["List of potential future issues"],
  "maintenanceRecommendations": ["Maintenance recommendations"],
  "capacityForecast": "Capacity and growth forecast"
}`;
  }

  /**
   * Apply results from an analysis agent to the report
   */
  private applyAgentResults(
    report: NodeAnalysisReport,
    agentType: AnalysisAgent,
    results: Record<string, unknown>
  ): void {
    switch (agentType) {
      case 'performance':
        if (results.summary) report.performanceAnalysis.summary = results.summary as string;
        if (results.anomalies) report.performanceAnalysis.anomalies = results.anomalies as string[];
        if (results.comparisonToFleet) report.performanceAnalysis.comparisonToFleet = results.comparisonToFleet as string;
        if (results.interpretations) {
          const interps = results.interpretations as Record<string, string>;
          report.performanceAnalysis.kpiTrends.forEach(kpi => {
            const key = kpi.metric.toLowerCase().replace(/ /g, '_');
            if (interps[key]) kpi.interpretation = interps[key];
          });
        }
        break;

      case 'equipment':
        if (results.summary) report.equipmentStatus.summary = results.summary as string;
        if (results.hardwareHealth) report.equipmentStatus.hardwareHealth = results.hardwareHealth as string;
        if (results.firmwareStatus) report.equipmentStatus.firmwareStatus = results.firmwareStatus as string;
        if (results.maintenanceNeeds) report.equipmentStatus.maintenanceNeeds = results.maintenanceNeeds as string[];
        if (results.endOfLifeWarnings) report.equipmentStatus.endOfLifeWarnings = results.endOfLifeWarnings as string[];
        break;

      case 'alerts':
        if (results.commonIssues) report.alertAnalysis.commonIssues = results.commonIssues as string[];
        if (results.patternAnalysis) report.alertAnalysis.patternAnalysis = results.patternAnalysis as string;
        break;

      case 'remediation':
        if (results.mostEffectiveActions) report.remediationAnalysis.mostEffectiveActions = results.mostEffectiveActions as string[];
        if (results.improvementSuggestions) report.remediationAnalysis.improvementSuggestions = results.improvementSuggestions as string[];
        break;

      case 'predictive':
        if (typeof results.riskScore === 'number') report.predictiveInsights.riskScore = results.riskScore;
        if (results.potentialIssues) report.predictiveInsights.potentialIssues = results.potentialIssues as string[];
        if (results.maintenanceRecommendations) report.predictiveInsights.maintenanceRecommendations = results.maintenanceRecommendations as string[];
        if (results.capacityForecast) report.predictiveInsights.capacityForecast = results.capacityForecast as string;
        break;
    }
  }

  /**
   * Generate executive summary using all collected data
   */
  private async generateExecutiveSummary(
    report: NodeAnalysisReport,
    node: FiberNode,
    _kpis: KPIMetrics[],
    alerts: Alert[],
    _actions: SelfHealingAction[]
  ): Promise<void> {
    const summaryPrompt = `Generate an executive summary for this node analysis:

Node: ${node.node_id} (${node.city}, ${node.region})
Status: ${node.status}
Health Score: ${report.executiveSummary.healthScore}/100

Performance Summary: ${report.performanceAnalysis.summary || 'Not available'}
Equipment Summary: ${report.equipmentStatus.summary || 'Not available'}
Active Alerts: ${report.alertAnalysis.activeAlerts}
Critical Alerts: ${report.alertAnalysis.criticalAlerts}
Remediation Success Rate: ${report.remediationAnalysis.successRate.toFixed(1)}%
Risk Score: ${report.predictiveInsights.riskScore}/100

Provide an executive summary in this JSON format:
{
  "keyFindings": ["3-5 key findings"],
  "urgentIssues": ["Any urgent issues requiring immediate attention"],
  "recommendations": ["3-5 top recommendations"]
}`;

    const messages: LLMMessage[] = [
      {
        role: 'system',
        content: `You are an expert cable/ISP network analyst creating executive summaries.
Be concise, actionable, and prioritize critical issues.
Respond ONLY with valid JSON.`,
      },
      {
        role: 'user',
        content: summaryPrompt,
      },
    ];

    const response = await llmService.complete(messages);
    if (response) {
      try {
        const jsonMatch = response.content.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          const results = JSON.parse(jsonMatch[0]);
          if (results.keyFindings) report.executiveSummary.keyFindings = results.keyFindings;
          if (results.urgentIssues) report.executiveSummary.urgentIssues = results.urgentIssues;
          if (results.recommendations) report.executiveSummary.recommendations = results.recommendations;
        }
      } catch (e) {
        console.error('Failed to parse executive summary:', e);
      }
    }

    // If LLM failed, generate basic findings
    if (report.executiveSummary.keyFindings.length === 0) {
      await this.generateBasicFindings(report, node, alerts, _actions);
    }
  }

  /**
   * Populate equipment status from sensor data (called regardless of LLM availability)
   */
  private populateEquipmentFromSensors(
    report: NodeAnalysisReport,
    node: FiberNode
  ): void {
    // Equipment summary
    const daysSinceMaintenance = Math.floor(
      (Date.now() - toDate(node.last_maintenance).getTime()) / (1000 * 60 * 60 * 24)
    );

    // Get sensor data for this node - generate on-demand if not available
    let sensorData = getAllSensorData(node.node_id);

    // If no sensor data exists, generate it on-demand for this node
    if (!sensorData.equipment || !sensorData.antenna || !sensorData.environmental) {
      console.log(`Generating sensor data on-demand for node ${node.node_id}`);
      const generatedSensors = generateAllSensorData(node, new Date());

      // Insert the generated sensor data into the store
      if (generatedSensors.antenna) {
        insertAntennaSensors([generatedSensors.antenna]);
      }
      if (generatedSensors.weather) {
        insertWeatherData([generatedSensors.weather]);
      }
      if (generatedSensors.environmental) {
        insertEnvSensors([generatedSensors.environmental]);
      }
      if (generatedSensors.equipment) {
        insertEquipmentSensors([generatedSensors.equipment]);
      }

      // Re-fetch sensor data after generation
      sensorData = getAllSensorData(node.node_id);
    }

    const equipmentSensor = sensorData.equipment;
    const antennaSensor = sensorData.antenna;
    const envSensor = sensorData.environmental;

    report.equipmentStatus.summary = `${node.manufacturer} ${node.hardware_model} with firmware ${node.firmware_version}. ` +
      `Last maintenance was ${daysSinceMaintenance} days ago.`;

    // Detailed hardware health assessment from sensor data
    if (equipmentSensor && equipmentSensor.component_health.length > 0) {
      const healthyComponents = equipmentSensor.component_health.filter(c => c.status === 'healthy').length;
      const degradedComponents = equipmentSensor.component_health.filter(c => c.status === 'degraded').length;
      const criticalComponents = equipmentSensor.component_health.filter(c => c.status === 'critical' || c.status === 'failed').length;
      const totalComponents = equipmentSensor.component_health.length;
      const avgHealthScore = equipmentSensor.component_health.reduce((s, c) => s + c.health_score, 0) / totalComponents;

      // Build detailed hardware health string
      const healthDetails: string[] = [];
      if (criticalComponents > 0) {
        const criticalNames = equipmentSensor.component_health
          .filter(c => c.status === 'critical' || c.status === 'failed')
          .map(c => c.component_name)
          .join(', ');
        healthDetails.push(`${criticalComponents} CRITICAL component(s): ${criticalNames}`);
      }
      if (degradedComponents > 0) {
        const degradedNames = equipmentSensor.component_health
          .filter(c => c.status === 'degraded')
          .map(c => c.component_name)
          .join(', ');
        healthDetails.push(`${degradedComponents} degraded component(s): ${degradedNames}`);
      }
      healthDetails.push(`${healthyComponents}/${totalComponents} components healthy (${avgHealthScore.toFixed(0)}% avg health score)`);

      // Add error logs if significant
      if (equipmentSensor.error_log_count > 10) {
        healthDetails.push(`High error count: ${equipmentSensor.error_log_count} errors in last 24h`);
      }

      report.equipmentStatus.hardwareHealth = healthDetails.join('. ');

      // Add maintenance needs from degraded/critical components
      equipmentSensor.component_health.forEach(comp => {
        if (comp.status === 'critical' || comp.status === 'failed') {
          report.equipmentStatus.maintenanceNeeds.push(`URGENT: Replace/repair ${comp.component_name} (${Math.round(comp.health_score)}% health)`);
        } else if (comp.status === 'degraded') {
          report.equipmentStatus.maintenanceNeeds.push(`Schedule maintenance for ${comp.component_name} (${Math.round(comp.health_score)}% health)`);
        }
        // Check for components with low remaining life
        if (comp.estimated_remaining_life_days && comp.estimated_remaining_life_days <= 30) {
          report.equipmentStatus.endOfLifeWarnings.push(`${comp.component_name} has ~${comp.estimated_remaining_life_days} days remaining life`);
        } else if (comp.estimated_remaining_life_days && comp.estimated_remaining_life_days <= 60) {
          report.predictiveInsights.maintenanceRecommendations.push(`Plan replacement for ${comp.component_name} (~${comp.estimated_remaining_life_days} days remaining)`);
        }
      });

      // Firmware status from sensor data
      report.equipmentStatus.firmwareStatus = `Firmware: ${equipmentSensor.firmware_version}. ` +
        `Uptime: ${Math.floor(equipmentSensor.uptime_hours / 24)} days. ` +
        `Last reboot: ${toDate(equipmentSensor.last_reboot).toLocaleDateString()}`;
    } else {
      // Fallback if no sensor data
      report.equipmentStatus.hardwareHealth = node.status === 'healthy'
        ? 'Hardware operating within normal parameters (no sensor data available)'
        : `Hardware may need attention - node status is ${node.status} (no sensor data available)`;
      report.equipmentStatus.firmwareStatus = `Firmware ${node.firmware_version} - sensor data not available for detailed assessment`;
    }

    // Add antenna sensor data if available
    if (antennaSensor) {
      if (antennaSensor.mechanical_health < 70) {
        report.equipmentStatus.maintenanceNeeds.push(`Antenna mechanical health low: ${antennaSensor.mechanical_health}%`);
      }
      if (antennaSensor.motor_status !== 'operational') {
        report.equipmentStatus.maintenanceNeeds.push(`Antenna motor ${antennaSensor.motor_status}`);
      }
      if (Math.abs(antennaSensor.azimuth_drift) > 2 || Math.abs(antennaSensor.tilt_drift) > 1) {
        report.equipmentStatus.maintenanceNeeds.push(
          `Antenna calibration needed: azimuth drift ${antennaSensor.azimuth_drift.toFixed(1)}°, tilt drift ${antennaSensor.tilt_drift.toFixed(1)}°`
        );
      }
    }

    // Add environmental sensor data if available
    if (envSensor) {
      if (envSensor.power_quality < 80) {
        report.equipmentStatus.maintenanceNeeds.push(`Power quality issues: ${envSensor.power_quality}% stability`);
      }
      if (envSensor.backup_battery_level < 50) {
        report.equipmentStatus.maintenanceNeeds.push(`Low backup battery: ${envSensor.backup_battery_level}%`);
      }
      if (envSensor.cabinet_temperature > 45) {
        report.equipmentStatus.maintenanceNeeds.push(`Cabinet overheating: ${envSensor.cabinet_temperature}°C`);
      }
      if (envSensor.door_status !== 'closed') {
        report.equipmentStatus.maintenanceNeeds.push(`Security issue: cabinet door ${envSensor.door_status}`);
      }
    }
  }

  /**
   * Generate rule-based analysis without LLM
   * Note: Equipment sensor data is already populated by populateEquipmentFromSensors()
   */
  private async generateRuleBasedAnalysis(
    report: NodeAnalysisReport,
    node: FiberNode,
    kpis: KPIMetrics[],
    alerts: Alert[],
    actions: SelfHealingAction[]
  ): Promise<void> {
    // Performance summary
    const avgSnr = kpis.length > 0
      ? kpis.reduce((s, k) => s + k.ds_snr_db, 0) / kpis.length
      : 0;

    report.performanceAnalysis.summary =
      avgSnr >= 38 ? 'Excellent performance with consistently high KPIs' :
      avgSnr >= 33 ? 'Good performance with minor fluctuations' :
      avgSnr >= 28 ? 'Fair performance with room for improvement' :
      'Performance issues detected requiring attention';

    const daysSinceMaintenance = Math.floor(
      (Date.now() - toDate(node.last_maintenance).getTime()) / (1000 * 60 * 60 * 24)
    );

    // Alert patterns
    const alertTypes = new Set(alerts.map(a => a.alert_type));
    report.alertAnalysis.commonIssues = Array.from(alertTypes).map(t =>
      `${t.replace(/_/g, ' ').toLowerCase()} issues detected`
    );

    report.alertAnalysis.patternAnalysis = alerts.length > 10
      ? 'High alert volume indicates potential systemic issues'
      : alerts.length > 0
        ? 'Normal alert patterns detected'
        : 'No significant alert patterns';

    // Generate basic findings
    await this.generateBasicFindings(report, node, alerts, actions);

    // Add KPI interpretations (accounting for metrics where lower is better)
    const lowerIsBetterMetrics = ['Packet Loss', 'Latency'];
    report.performanceAnalysis.kpiTrends.forEach(kpi => {
      const isLowerBetter = lowerIsBetterMetrics.includes(kpi.metric);

      if (kpi.trend === 'improving') {
        // For lower-is-better metrics, improving means value went DOWN
        kpi.interpretation = isLowerBetter
          ? `${kpi.metric} is decreasing - positive indicator`
          : `${kpi.metric} is trending upward - positive indicator`;
      } else if (kpi.trend === 'declining') {
        // For lower-is-better metrics, declining means value went UP (bad)
        kpi.interpretation = isLowerBetter
          ? `${kpi.metric} is increasing - may need attention`
          : `${kpi.metric} is trending downward - may need attention`;
      } else {
        kpi.interpretation = `${kpi.metric} is stable within normal range`;
      }
    });

    // Predictive insights
    report.predictiveInsights.riskScore =
      node.status === 'outage' ? 90 :
      node.status === 'degraded' ? 60 :
      report.alertAnalysis.activeAlerts > 5 ? 50 :
      report.alertAnalysis.activeAlerts > 0 ? 30 : 10;

    const daysUntilMaintenanceRuleBased = Math.floor(
      (new Date(toDate(node.last_maintenance).getTime() + 90 * 24 * 60 * 60 * 1000).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    );

    if (daysUntilMaintenanceRuleBased <= 7) {
      report.predictiveInsights.maintenanceRecommendations.push('Scheduled maintenance due within 7 days');
    }
    if (daysSinceMaintenance > 90) {
      report.predictiveInsights.maintenanceRecommendations.push('Consider maintenance review - over 90 days since last service');
    }

    // Generate potential issues based on current data patterns
    report.predictiveInsights.potentialIssues = this.generatePotentialIssues(
      node, kpis, alerts, actions, report
    );

    // Generate capacity forecast
    report.predictiveInsights.capacityForecast = this.generateCapacityForecast(
      node, kpis
    );
  }

  /**
   * Fill in predictive insights with rule-based fallbacks when LLM fails
   */
  private fillPredictiveInsightsFallback(
    report: NodeAnalysisReport,
    node: FiberNode,
    kpis: KPIMetrics[],
    alerts: Alert[],
    actions: SelfHealingAction[]
  ): void {
    // Fill risk score if not set or zero
    if (!report.predictiveInsights.riskScore) {
      report.predictiveInsights.riskScore =
        node.status === 'outage' ? 90 :
        node.status === 'degraded' ? 60 :
        report.alertAnalysis.activeAlerts > 5 ? 50 :
        report.alertAnalysis.activeAlerts > 0 ? 30 : 10;
    }

    // Fill potential issues if empty
    if (report.predictiveInsights.potentialIssues.length === 0) {
      report.predictiveInsights.potentialIssues = this.generatePotentialIssues(
        node, kpis, alerts, actions, report
      );
    }

    // Fill capacity forecast if empty
    if (!report.predictiveInsights.capacityForecast) {
      report.predictiveInsights.capacityForecast = this.generateCapacityForecast(node, kpis);
    }

    // Fill maintenance recommendations if empty
    if (report.predictiveInsights.maintenanceRecommendations.length === 0) {
      const daysSinceMaintenance = Math.floor(
        (Date.now() - toDate(node.last_maintenance).getTime()) / (1000 * 60 * 60 * 24)
      );
      const daysUntilMaintenance = Math.floor(
        (new Date(toDate(node.last_maintenance).getTime() + 90 * 24 * 60 * 60 * 1000).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
      );

      if (daysUntilMaintenance <= 7) {
        report.predictiveInsights.maintenanceRecommendations.push('Scheduled maintenance due within 7 days');
      }
      if (daysSinceMaintenance > 90) {
        report.predictiveInsights.maintenanceRecommendations.push('Consider maintenance review - over 90 days since last service');
      }
      if (report.predictiveInsights.maintenanceRecommendations.length === 0) {
        report.predictiveInsights.maintenanceRecommendations.push('Continue routine monitoring - no urgent maintenance required');
      }
    }

    // Fill alert pattern analysis if empty
    if (!report.alertAnalysis.patternAnalysis) {
      report.alertAnalysis.patternAnalysis = alerts.length > 10
        ? 'High alert volume indicates potential systemic issues'
        : alerts.length > 0
          ? 'Normal alert patterns detected'
          : 'No significant alert patterns';
    }

    // Fill common issues if empty
    if (report.alertAnalysis.commonIssues.length === 0 && alerts.length > 0) {
      const alertTypes = new Set(alerts.map(a => a.alert_type));
      report.alertAnalysis.commonIssues = Array.from(alertTypes).slice(0, 5).map(t =>
        `${(t || 'unknown').replace(/_/g, ' ').toLowerCase()} issues detected`
      );
    }
  }

  /**
   * Generate potential issues based on data patterns (rule-based)
   */
  private generatePotentialIssues(
    node: FiberNode,
    kpis: KPIMetrics[],
    alerts: Alert[],
    actions: SelfHealingAction[],
    report: NodeAnalysisReport
  ): string[] {
    const issues: string[] = [];

    // Check for declining KPI trends
    if (kpis.length >= 10) {
      const recentKpis = kpis.slice(-10);
      const olderKpis = kpis.slice(-20, -10);

      if (olderKpis.length >= 5) {
        const recentAvgSnr = recentKpis.reduce((s, k) => s + k.ds_snr_db, 0) / recentKpis.length;
        const olderAvgSnr = olderKpis.reduce((s, k) => s + k.ds_snr_db, 0) / olderKpis.length;

        if (recentAvgSnr < olderAvgSnr - 2) {
          issues.push(`DS SNR declining (${olderAvgSnr.toFixed(1)} dB → ${recentAvgSnr.toFixed(1)} dB)`);
        }

        const recentAvgLoss = recentKpis.reduce((s, k) => s + k.packet_loss_percent, 0) / recentKpis.length;
        const olderAvgLoss = olderKpis.reduce((s, k) => s + k.packet_loss_percent, 0) / olderKpis.length;

        if (recentAvgLoss > olderAvgLoss + 0.5) {
          issues.push(`Packet loss increasing (${olderAvgLoss.toFixed(2)}% → ${recentAvgLoss.toFixed(2)}%)`);
        }

        const recentAvgThroughput = recentKpis.reduce((s, k) => s + k.downstream_throughput_mbps, 0) / recentKpis.length;
        const olderAvgThroughput = olderKpis.reduce((s, k) => s + k.downstream_throughput_mbps, 0) / olderKpis.length;

        if (recentAvgThroughput < olderAvgThroughput * 0.9) {
          issues.push(`Throughput degrading (${olderAvgThroughput.toFixed(1)} → ${recentAvgThroughput.toFixed(1)} Mbps)`);
        }
      }
    }

    // Check for recurring alert patterns
    const alertTypeCount: Record<string, number> = {};
    alerts.forEach(a => {
      alertTypeCount[a.alert_type] = (alertTypeCount[a.alert_type] || 0) + 1;
    });

    Object.entries(alertTypeCount).forEach(([alertType, count]) => {
      if (count >= 5) {
        issues.push(`Recurring ${alertType.replace(/_/g, ' ').toLowerCase()} issues (${count} occurrences)`);
      }
    });

    // Check for high failure rate in remediation
    const failedActions = actions.filter(a => a.status === 'failed').length;
    const totalActions = actions.length;
    if (totalActions > 5 && failedActions / totalActions > 0.3) {
      issues.push(`High remediation failure rate (${((failedActions / totalActions) * 100).toFixed(0)}%) - may indicate underlying hardware issue`);
    }

    // Check equipment status for warnings
    if (report.equipmentStatus.endOfLifeWarnings.length > 0) {
      issues.push(`${report.equipmentStatus.endOfLifeWarnings.length} component(s) approaching end of life`);
    }

    // Check maintenance overdue
    const daysSinceMaintenance = Math.floor(
      (Date.now() - toDate(node.last_maintenance).getTime()) / (1000 * 60 * 60 * 24)
    );
    if (daysSinceMaintenance > 120) {
      issues.push(`Extended period since maintenance (${daysSinceMaintenance} days) - risk of undetected issues`);
    }

    // Check for high latency trend
    if (kpis.length >= 5) {
      const recentLatency = kpis.slice(-5).reduce((s, k) => s + k.latency_ms, 0) / 5;
      if (recentLatency > 100) {
        issues.push(`Elevated latency detected (${recentLatency.toFixed(0)}ms average) - may impact user experience`);
      }
    }

    // If no specific issues found, provide general assessment
    if (issues.length === 0) {
      if (node.status === 'healthy') {
        issues.push('No immediate issues predicted - node operating within normal parameters');
      } else {
        issues.push(`Node in ${node.status} state - monitor for potential escalation`);
      }
    }

    return issues;
  }

  /**
   * Generate capacity forecast based on KPI data (rule-based)
   */
  private generateCapacityForecast(
    _node: FiberNode,
    kpis: KPIMetrics[]
  ): string {
    if (kpis.length < 5) {
      return 'Insufficient data for capacity forecast - requires more historical KPI records';
    }

    // Analyze recent traffic patterns
    const recentKpis = kpis.slice(-20);
    const avgActiveModems = recentKpis.reduce((s, k) => s + k.active_modems, 0) / recentKpis.length;
    const maxActiveModems = Math.max(...recentKpis.map(k => k.active_modems));
    const avgThroughput = recentKpis.reduce((s, k) => s + k.downstream_throughput_mbps, 0) / recentKpis.length;
    const avgCpuUtil = recentKpis.reduce((s, k) => s + k.node_cpu_utilization, 0) / recentKpis.length;

    let forecast = '';

    if (avgCpuUtil > 85) {
      forecast = `HIGH LOAD: CPU utilization at ${avgCpuUtil.toFixed(0)}%. `;
      forecast += `Current average modems: ${avgActiveModems.toFixed(0)} (peak: ${maxActiveModems}). `;
      forecast += 'Recommend capacity expansion or load balancing within 30 days to prevent service degradation.';
    } else if (avgCpuUtil > 70) {
      forecast = `MODERATE LOAD: CPU utilization at ${avgCpuUtil.toFixed(0)}%. `;
      forecast += `Current average modems: ${avgActiveModems.toFixed(0)} (peak: ${maxActiveModems}). `;
      forecast += 'Monitor closely for capacity needs in 60-90 days if growth continues.';
    } else if (avgCpuUtil > 50) {
      forecast = `NORMAL LOAD: CPU utilization at ${avgCpuUtil.toFixed(0)}%. `;
      forecast += `Current average modems: ${avgActiveModems.toFixed(0)} with ${avgThroughput.toFixed(1)} Mbps average throughput. `;
      forecast += 'Adequate capacity for current demand with room for growth.';
    } else {
      forecast = `LOW LOAD: CPU utilization at ${avgCpuUtil.toFixed(0)}%. `;
      forecast += `Current average modems: ${avgActiveModems.toFixed(0)}. `;
      forecast += 'Significant spare capacity available. Consider load balancing from neighboring nodes if applicable.';
    }

    return forecast;
  }

  /**
   * Generate basic findings from data
   */
  private async generateBasicFindings(
    report: NodeAnalysisReport,
    node: FiberNode,
    alerts: Alert[],
    _actions: SelfHealingAction[]
  ): Promise<void> {
    // Fetch equipment data from API (history data shown in graphs, not needed here)
    let equipmentData: EquipmentAPIResponse | null = null;

    try {
      equipmentData = await apiClient.get<EquipmentAPIResponse>(`/nodes/${node.node_id}/equipment`);
    } catch (error) {
      console.warn('Failed to fetch equipment data for findings:', error);
    }

    // Key findings - now includes equipment status
    report.executiveSummary.keyFindings = [
      `Node is currently ${node.status} with ${report.executiveSummary.healthScore}% health score`,
      `${alerts.length} alerts recorded with ${report.alertAnalysis.activeAlerts} currently active`,
      `Remediation success rate: ${report.remediationAnalysis.successRate.toFixed(1)}%`,
    ];

    // Add equipment findings - concise summary only (detailed graphs shown in Equipment Status section)
    if (equipmentData) {
      const operationalAAUs = equipmentData.aau_units.filter(a => a.status === 'operational').length;
      const degradedAAUs = equipmentData.aau_units.filter(a => a.status !== 'operational');
      const loadPercent = (equipmentData.power.current_load_kw / equipmentData.power.max_load_kw) * 100;
      const avgAAUEfficiency = equipmentData.aau_units.reduce((sum, a) => sum + a.efficiency_percent, 0) / equipmentData.aau_units.length;

      // Build concise equipment summary
      const equipmentStatuses: string[] = [];

      // AAU status
      if (operationalAAUs === equipmentData.aau_units.length) {
        equipmentStatuses.push(`AAU: ${operationalAAUs}/${equipmentData.aau_units.length} operational`);
      } else {
        equipmentStatuses.push(`AAU: ${operationalAAUs}/${equipmentData.aau_units.length} operational (${degradedAAUs.length} degraded)`);
      }

      // BBU status
      equipmentStatuses.push(`BBU: ${equipmentData.bbu.status}`);

      // HVAC status
      equipmentStatuses.push(`HVAC: ${equipmentData.hvac.status}`);

      // Power/UPS status
      const powerStatus = equipmentData.power.grid_status === 'connected'
        ? `Power: Grid connected, UPS ${equipmentData.power.ups_status}`
        : `Power: Grid ${equipmentData.power.grid_status}, UPS ${equipmentData.power.ups_status}`;
      equipmentStatuses.push(powerStatus);

      // Add single-line equipment summary
      const overallHealth = equipmentData.summary.overall_health;
      const healthLabel = overallHealth === 'healthy' ? 'All systems nominal' : `Status: ${overallHealth.toUpperCase()}`;
      report.executiveSummary.keyFindings.push(
        `Equipment: ${healthLabel} — ${equipmentStatuses.join(' | ')}`
      );

      // Add equipment-related urgent issues with values
      if (equipmentData.hvac.high_temp_alarm) {
        report.executiveSummary.urgentIssues.push(`HVAC high temperature alarm - current temp ${equipmentData.hvac.current_temp_celsius.toFixed(1)}°C exceeds setpoint ${equipmentData.hvac.setpoint_celsius.toFixed(0)}°C`);
      }
      if (equipmentData.power.battery_health_percent < 70) {
        report.executiveSummary.urgentIssues.push(`Battery health critical at ${equipmentData.power.battery_health_percent.toFixed(0)}% - replacement recommended`);
      }
      if (equipmentData.bbu.cpu_utilization_percent > 85) {
        report.executiveSummary.urgentIssues.push(`BBU CPU utilization high at ${equipmentData.bbu.cpu_utilization_percent.toFixed(0)}% - may impact performance`);
      }
      if (equipmentData.bbu.memory_utilization_percent > 85) {
        report.executiveSummary.urgentIssues.push(`BBU memory utilization high at ${equipmentData.bbu.memory_utilization_percent.toFixed(0)}%`);
      }
      if (equipmentData.bbu.temperature_celsius > 55) {
        report.executiveSummary.urgentIssues.push(`BBU overheating at ${equipmentData.bbu.temperature_celsius.toFixed(1)}°C`);
      }
      if (loadPercent > 85) {
        report.executiveSummary.urgentIssues.push(`Power load critical at ${loadPercent.toFixed(0)}% capacity (${equipmentData.power.current_load_kw.toFixed(1)}/${equipmentData.power.max_load_kw.toFixed(1)}kW)`);
      }

      // Check for degraded AAU units with details
      if (degradedAAUs.length > 0) {
        const degradedList = degradedAAUs.map(a => `${a.aau_id.split('-').pop()}: ${a.status}`).join(', ');
        report.executiveSummary.urgentIssues.push(`${degradedAAUs.length} AAU unit(s) degraded/maintenance: ${degradedList}`);
      }

      // High temperature AAUs
      const hotAAUs = equipmentData.aau_units.filter(a => a.temperature_celsius > 55);
      if (hotAAUs.length > 0) {
        report.executiveSummary.urgentIssues.push(`${hotAAUs.length} AAU unit(s) overheating: ${hotAAUs.map(a => `${a.temperature_celsius.toFixed(0)}°C`).join(', ')}`);
      }

      // Add equipment-related recommendations with values
      if (equipmentData.power.battery_backup_hours < 4) {
        report.executiveSummary.recommendations.push(`Increase battery backup capacity from ${equipmentData.power.battery_backup_hours.toFixed(0)} hours to minimum 4 hours`);
      }
      if (equipmentData.power.battery_health_percent < 80 && equipmentData.power.battery_health_percent >= 70) {
        report.executiveSummary.recommendations.push(`Monitor battery health (${equipmentData.power.battery_health_percent.toFixed(0)}%) - consider replacement planning`);
      }
      if (equipmentData.hvac.compressor_status === 'fault') {
        report.executiveSummary.recommendations.push('Schedule HVAC compressor repair - cooling compromised');
      }
      if (avgAAUEfficiency < 80) {
        report.executiveSummary.recommendations.push(`AAU efficiency below target at ${avgAAUEfficiency.toFixed(1)}% - consider calibration`);
      }
      if (equipmentData.bbu.cpu_utilization_percent > 70 && equipmentData.bbu.cpu_utilization_percent <= 85) {
        report.executiveSummary.recommendations.push(`Monitor BBU CPU utilization (${equipmentData.bbu.cpu_utilization_percent.toFixed(0)}%) - approaching threshold`);
      }
    }

    // Urgent issues
    if (node.status === 'outage') {
      report.executiveSummary.urgentIssues.push('Node is in OUTAGE state - immediate attention required');
    }
    // Only count TRULY ACTIVE critical alerts for urgent issues
    // Must check BOTH status='active' AND resolved_at=null due to data inconsistency
    const activeCriticalCount = alerts.filter(a => a.status === 'active' && !a.resolved_at && a.severity === 'critical').length;
    if (activeCriticalCount > 0) {
      report.executiveSummary.urgentIssues.push(`${activeCriticalCount} critical alert${activeCriticalCount > 1 ? 's' : ''} currently active`);
    }
    if (report.remediationAnalysis.failedActions > 3) {
      report.executiveSummary.urgentIssues.push('Multiple remediation failures - manual intervention may be needed');
    }

    // Recommendations
    report.executiveSummary.recommendations = [];
    if (node.status !== 'healthy') {
      report.executiveSummary.recommendations.push('Investigate and resolve active issues to restore healthy status');
    }
    if (report.remediationAnalysis.successRate < 80) {
      report.executiveSummary.recommendations.push('Review remediation strategies - success rate below target');
    }

    const daysUntilMaintenanceBasic = Math.floor(
      (new Date(toDate(node.last_maintenance).getTime() + 90 * 24 * 60 * 60 * 1000).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    );
    if (daysUntilMaintenanceBasic <= 14) {
      report.executiveSummary.recommendations.push(`Schedule maintenance - due in ${daysUntilMaintenanceBasic} days`);
    }

    if (report.executiveSummary.recommendations.length === 0) {
      report.executiveSummary.recommendations.push('Continue routine monitoring');
    }
  }

  /**
   * Format duration from milliseconds to human-readable string
   */
  private formatDuration(ms: number): string {
    if (ms < 1000) return 'Less than 1 second';
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds} seconds`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''}`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ${minutes % 60}m`;
    const days = Math.floor(hours / 24);
    return `${days} day${days > 1 ? 's' : ''} ${hours % 24}h`;
  }
}

// Export singleton instance
export const nodeAnalysisService = new NodeAnalysisService();
