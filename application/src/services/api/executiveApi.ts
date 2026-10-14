/**
 * Executive API - Executive dashboard endpoints
 */

import { apiRequest } from './baseClient';

// ===== TYPES =====

export interface ExecutiveSummary {
  timestamp: string;
  period: string;
  // Network Health
  total_nodes: number;
  healthy_nodes: number;
  degraded_nodes: number;
  outage_nodes: number;
  maintenance_nodes: number;
  network_uptime_percent: number;
  // SLA Status
  sla_compliance_percent: number;
  active_sla_breaches: number;
  near_breach_warnings: number;
  breaches_this_period: number;
  // Financial Summary
  revenue_at_risk: number;
  revenue_protected: number;
  actual_revenue_loss: number;
  ai_cost_savings: number;
  sla_penalty_exposure: number;
  net_financial_impact: number;
  // Incident Summary
  total_alerts: number;
  critical_alerts: number;
  warning_alerts: number;
  auto_resolved: number;
  manual_interventions: number;
  avg_resolution_time_minutes: number;
  // Performance Metrics
  avg_latency_ms: number;
  avg_ds_snr_db: number;
  downstream_throughput_mbps: number;
  affected_subscribers_current: number;
  // Regional Breakdown
  regions: Array<{
    region: string;
    nodes: number;
    uptime: number;
    revenue_impact: number;
    alerts: number;
  }>;
  // Top Issues
  top_issues: Array<{
    node_id: string;
    issue_type: string;
    duration: number;
    impact: number;
  }>;
  // Trends
  trend_uptime: string;
  trend_incidents: string;
  trend_revenue_impact: string;
}

// ===== FUNCTIONS =====

export async function getExecutiveSummary(periodHours: number = 24): Promise<ExecutiveSummary> {
  return apiRequest(`/executive/summary?period_hours=${periodHours}`);
}
