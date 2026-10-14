/**
 * Analysis Agents - LLM agent definitions and prompt builders
 * Handles the 5 analysis agents: performance, equipment, alerts, remediation, predictive
 */

import { llmService } from '../llmService';
import { LLMMessage } from '@/types/llm';
import {
  FiberNode,
  KPIMetrics,
  Alert,
  SelfHealingAction,
} from '@/types';
import { AnalysisAgent, NodeAnalysisReport, toDate } from './types';

/**
 * Run an analysis agent with LLM
 */
export async function runAnalysisAgent(
  agentType: AnalysisAgent,
  node: FiberNode,
  kpis: KPIMetrics[],
  alerts: Alert[],
  actions: SelfHealingAction[]
): Promise<Record<string, unknown> | null> {
  const prompt = buildAgentPrompt(agentType, node, kpis, alerts, actions);

  const messages: LLMMessage[] = [
    {
      role: 'system',
      content: getAgentSystemPrompt(agentType),
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
function getAgentSystemPrompt(agentType: AnalysisAgent): string {
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
function buildAgentPrompt(
  agentType: AnalysisAgent,
  node: FiberNode,
  kpis: KPIMetrics[],
  alerts: Alert[],
  actions: SelfHealingAction[]
): string {
  const nodeInfo = `
Node: ${node.node_id}
Location: ${node.city || 'Unknown'}, ${node.region}
Status: ${node.status}
Manufacturer: ${node.manufacturer || 'Unknown'}
Model: ${node.hardware_model || 'Unknown'}
Firmware: ${node.firmware_version || 'Unknown'}
DOCSIS Version: ${node.docsis_version || '3.1'}
Node Type: ${node.node_type || 'N+0'}
Homes Passed: ${node.homes_passed || 0}
Homes Active: ${node.homes_active || 0}
Last Maintenance: ${toDate(node.last_maintenance).toISOString()}
`;

  switch (agentType) {
    case 'performance':
      return buildPerformancePrompt(nodeInfo, kpis);
    case 'equipment':
      return buildEquipmentPrompt(nodeInfo, node);
    case 'alerts':
      return buildAlertsPrompt(nodeInfo, alerts);
    case 'remediation':
      return buildRemediationPrompt(nodeInfo, actions);
    case 'predictive':
      return buildPredictivePrompt(nodeInfo, node, kpis, alerts, actions);
    default:
      return '';
  }
}

function buildPerformancePrompt(nodeInfo: string, kpis: KPIMetrics[]): string {
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

function buildEquipmentPrompt(nodeInfo: string, node: FiberNode): string {
  return `Analyze the equipment status for this node:

${nodeInfo}

Equipment Details:
- Hardware Model: ${node.hardware_model || 'Unknown'}
- Firmware Version: ${node.firmware_version || 'Unknown'}
- DOCSIS Version: ${node.docsis_version || '3.1'}
- Downstream Channels: ${node.downstream_channels || 0}
- Upstream Channels: ${node.upstream_channels || 0}
- OFDM Channels: ${node.ofdm_channels || 0}
- Power Supply Count: ${node.power_supply_count || 0}
- Power Supply Status: ${node.power_supply_status || 'unknown'}
- Battery Backup: ${node.battery_backup_hours || 0} hours
- Amplifier Cascade: ${node.amplifier_cascade || 0}
- Coax Plant Miles: ${node.coax_plant_miles || 0}
- Fiber Miles: ${node.fiber_miles || 0}

Provide analysis in this JSON format:
{
  "summary": "Overall equipment health summary",
  "hardwareHealth": "Assessment of hardware condition",
  "firmwareStatus": "Assessment of firmware/software versions",
  "maintenanceNeeds": ["List of maintenance recommendations"],
  "endOfLifeWarnings": ["Any end-of-life concerns"]
}`;
}

function buildAlertsPrompt(nodeInfo: string, alerts: Alert[]): string {
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

function buildRemediationPrompt(nodeInfo: string, actions: SelfHealingAction[]): string {
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

function buildPredictivePrompt(
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

  return `Provide predictive analysis for this node:

${nodeInfo}

Current Metrics (Avg of last 100 samples):
- DS SNR: ${avgMetrics.ds_snr.toFixed(1)} dB
- Packet Loss: ${avgMetrics.pkt_loss.toFixed(2)}%
- Active Modems: ${avgMetrics.modems.toFixed(0)}
- Homes Active: ${homesActive}
- Utilization: ${((avgMetrics.modems / Math.max(homesActive, 1)) * 100).toFixed(1)}%

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
export function applyAgentResults(
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
 * Generate executive summary using all collected data via LLM
 */
export async function generateExecutiveSummary(
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
    const { generateBasicFindings } = await import('./ruleBasedAnalysis');
    await generateBasicFindings(report, node, alerts, _actions);
  }
}
