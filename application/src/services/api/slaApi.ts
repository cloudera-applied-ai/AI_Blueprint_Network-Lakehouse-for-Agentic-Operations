/**
 * SLA API - SLA status and financial summary endpoints
 */

import { apiRequest } from './baseClient';

// ===== TYPES =====

export interface SLAConfig {
  uptime_target_percent: number;
  max_latency_ms: number;
  max_packet_loss_percent: number;
  min_ds_snr_db: number;
  warning_threshold_percent: number;
  critical_threshold_percent: number;
  created_at: string;
  updated_at?: string;
}

export interface SLAStatus {
  config: SLAConfig;
  current_uptime_percent: number;
  monthly_downtime_minutes: number;
  current_latency_avg_ms: number;
  current_ds_snr_db: number;
  current_packet_loss_percent: number;
  active_breaches: number;
  warning_alerts: number;
  breaches_this_month: number;
  total_penalty_exposure: number;
  status: 'healthy' | 'warning' | 'breach';
}

export interface FinancialSummary {
  id: number;
  summary_id: string;
  period_type: string;
  period_start: string;
  period_end: string;
  region?: string;
  total_revenue_at_risk: number;
  actual_revenue_loss: number;
  revenue_protected: number;
  operational_costs: number;
  sla_penalties: number;
  ai_savings: number;
  total_incidents: number;
  auto_resolved_incidents: number;
  manual_interventions: number;
  avg_resolution_time_minutes: number;
  uptime_percent: number;
  sla_breaches: number;
  near_breaches: number;
  created_at: string;
}

// ===== FUNCTIONS =====

export async function getSLAStatus(): Promise<SLAStatus> {
  return apiRequest('/sla/status');
}

export async function getFinancialSummary(periodDays: number = 30): Promise<FinancialSummary> {
  return apiRequest(`/financial/summary?period_days=${periodDays}`);
}
