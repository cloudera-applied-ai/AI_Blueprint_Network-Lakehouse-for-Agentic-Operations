/**
 * Rule-Based Analysis - Fallback analysis when LLM is not available
 * Includes issue detection logic and capacity forecast calculations
 */

import {
  FiberNode,
  KPIMetrics,
  Alert,
  SelfHealingAction,
} from '@/types';
import { apiClient } from '../apiClient';
import { NodeAnalysisReport, EquipmentAPIResponse, toDate } from './types';

/**
 * Generate rule-based analysis without LLM
 * Note: Equipment sensor data is already populated by populateEquipmentFromSensors()
 */
export async function generateRuleBasedAnalysis(
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
  await generateBasicFindings(report, node, alerts, actions);

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

  // Estimate next maintenance based on last maintenance + 90 day cycle
  const estimatedNextMaintenance = new Date(toDate(node.last_maintenance).getTime() + 90 * 24 * 60 * 60 * 1000);
  const daysUntilMaintenanceRuleBased = Math.floor(
    (estimatedNextMaintenance.getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  );

  if (daysUntilMaintenanceRuleBased <= 7) {
    report.predictiveInsights.maintenanceRecommendations.push('Scheduled maintenance due within 7 days');
  }
  if (daysSinceMaintenance > 90) {
    report.predictiveInsights.maintenanceRecommendations.push('Consider maintenance review - over 90 days since last service');
  }

  // Generate potential issues based on current data patterns
  report.predictiveInsights.potentialIssues = generatePotentialIssues(
    node, kpis, alerts, actions, report
  );

  // Generate capacity forecast
  report.predictiveInsights.capacityForecast = generateCapacityForecast(
    node, kpis
  );
}

/**
 * Fill in predictive insights with rule-based fallbacks when LLM fails
 */
export function fillPredictiveInsightsFallback(
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
    report.predictiveInsights.potentialIssues = generatePotentialIssues(
      node, kpis, alerts, actions, report
    );
  }

  // Fill capacity forecast if empty
  if (!report.predictiveInsights.capacityForecast) {
    report.predictiveInsights.capacityForecast = generateCapacityForecast(node, kpis);
  }

  // Fill maintenance recommendations if empty
  if (report.predictiveInsights.maintenanceRecommendations.length === 0) {
    const daysSinceMaintenance = Math.floor(
      (Date.now() - toDate(node.last_maintenance).getTime()) / (1000 * 60 * 60 * 24)
    );
    // Estimate next maintenance based on last maintenance + 90 day cycle
    const estimatedNextMaintenanceFallback = new Date(toDate(node.last_maintenance).getTime() + 90 * 24 * 60 * 60 * 1000);
    const daysUntilMaintenance = Math.floor(
      (estimatedNextMaintenanceFallback.getTime() - Date.now()) / (1000 * 60 * 60 * 24)
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
export function generatePotentialIssues(
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
export function generateCapacityForecast(
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
export async function generateBasicFindings(
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

  // Estimate next maintenance based on last maintenance + 90 day cycle
  const estimatedNextMaintenanceBasic = new Date(toDate(node.last_maintenance).getTime() + 90 * 24 * 60 * 60 * 1000);
  const daysUntilMaintenanceBasic = Math.floor(
    (estimatedNextMaintenanceBasic.getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  );
  if (daysUntilMaintenanceBasic <= 14) {
    report.executiveSummary.recommendations.push(`Schedule maintenance - due in ${daysUntilMaintenanceBasic} days`);
  }

  if (report.executiveSummary.recommendations.length === 0) {
    report.executiveSummary.recommendations.push('Continue routine monitoring');
  }
}
