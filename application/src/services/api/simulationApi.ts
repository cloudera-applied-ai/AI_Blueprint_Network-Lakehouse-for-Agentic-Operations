/**
 * Simulation API - Digital twin / simulation endpoints
 */

import { apiRequest } from './baseClient';
import type { CapacityForecast, BandwidthBottleneck, CapacityConstraint } from './capacityPlanningApi';

// ===== TYPES =====

export interface SimulatedMetrics {
  uptime_percent: number;
  latency_ms: number;
  throughput_mbps: number;
  packet_loss_percent: number;
  modems_affected?: number;
  backhaul_utilization?: number;
  recovery_time_minutes?: number;
  cascade_impact?: number;
  capacity_utilization?: number;
  scenario_type?: string;
  // Capacity planning fields
  trend_direction?: string;
  growth_rate_percent_per_month?: number;
  current_node_utilization?: number;
  current_dc_utilization?: number;
  current_bandwidth_utilization?: number;
  total_active_modems?: number;
  total_throughput_gbps?: number;
  forecasts?: CapacityForecast[];
  bandwidth_bottlenecks?: BandwidthBottleneck[];
  capacity_constraints?: CapacityConstraint[];
  analysis_time_ms?: number;
  [key: string]: number | string | CapacityForecast[] | BandwidthBottleneck[] | CapacityConstraint[] | undefined;
}

export interface BaselineMetrics {
  uptime_percent: number;
  latency_ms: number;
  throughput_mbps: number;
  packet_loss_percent: number;
  active_modems?: number;
  backhaul_capacity?: number;
  datacenter_latency_ms?: number;
  data_source?: string;  // Historical data source used for baselines
  [key: string]: number | string | undefined;
}

export interface SimulationResult {
  id: number;
  result_id: string;
  scenario_id: string;
  simulation_start: string;
  simulation_end?: string;
  duration_seconds?: number;
  baseline_metrics: BaselineMetrics;
  simulated_metrics: SimulatedMetrics;
  affected_nodes: string[];
  affected_node_count: number;
  affected_customers_estimated: number;
  affected_regions: string[];
  cascading_failures?: string[];
  neighbor_overload?: Record<string, number>;
  projected_revenue_loss: number;
  projected_sla_breaches: number;
  projected_penalty_cost: number;
  estimated_recovery_time_minutes?: number;
  recommended_actions: Array<{ action: string; priority: number }>;
  risk_score: number;
  executive_summary?: string;
  created_at: string;
}

export interface SimulationResultListResponse {
  total: number;
  items: SimulationResult[];
}

export interface RunSimulationRequest {
  scenario_id?: string;
  scenario_type?: string;
  target_nodes?: string[];
  target_regions?: string[];
  target_count?: number;
  parameters?: Record<string, unknown>;
  region?: string;
  time_of_day?: 'peak' | 'normal' | 'off_peak';
  node_types?: string[];
  cascading_failure?: boolean;
  recovery_strategy?: 'manual' | 'ai_assisted';
  custom_sla_uptime?: number;
  custom_sla_latency?: number;
  backhaul_capacity_percent?: number;
  datacenter_latency_ms?: number;
  network_congestion_factor?: number;
  packet_loss_percent?: number;
}

// ===== HISTORICAL CONTEXT TYPES =====

export interface HistoricalBaselines {
  kpi_baselines: {
    ds_snr_db?: number;
    packet_loss_percent?: number;
    us_snr_db?: number;
    latency_ms?: number;
    throughput_mbps?: number;
    active_modems?: number;
    node_cpu_utilization?: number;
    node_memory_utilization?: number;
    node_temperature?: number;
    total_samples?: number;
    data_source?: string;
  };
  incident_baselines: {
    total_actions?: number;
    completed_actions?: number;
    failed_actions?: number;
    pending_actions?: number;
    success_rate?: number;
    mttr_minutes?: number;
    min_resolution_time_minutes?: number;
    max_resolution_time_minutes?: number;
    avg_effectiveness?: number;
  };
  network_baselines: {
    total_nodes?: number;
    healthy_nodes?: number;
    uptime_percent?: number;
    avg_alerts_per_hour?: number;
  };
  period_hours: number;
  calculated_at: string;
}

export interface SimilarHistoricalIncident {
  action_id: string;
  action_type: string;
  node_id: string;
  duration_minutes: number;
  effectiveness_score: number | null;
  timestamp: string | null;
  outcome: string;
}

export interface SimulationHistoricalContext {
  baselines: HistoricalBaselines;
  similar_incidents: SimilarHistoricalIncident[];
  alert_patterns: {
    total_alerts?: number;
    by_type?: Record<string, number>;
    by_severity?: Record<string, number>;
    by_hour?: Record<string, number>;
    peak_hours?: Array<{ hour: number; count: number }>;
    period_hours?: number;
  };
  data_availability: Record<string, { records: number; has_data: boolean }>;
  confidence_score: number;
}

// ===== FUNCTIONS =====

export async function runSimulation(request: RunSimulationRequest): Promise<SimulationResult> {
  return apiRequest('/simulation/run', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getSimulationResults(params: {
  skip?: number;
  limit?: number;
  scenario_type?: string;
} = {}): Promise<SimulationResultListResponse> {
  const queryParams = new URLSearchParams();
  if (params.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params.scenario_type) queryParams.append('scenario_type', params.scenario_type);

  return apiRequest(`/simulation/results?${queryParams.toString()}`);
}

export async function deleteSimulationResult(resultId: string): Promise<{ message: string }> {
  return apiRequest(`/simulation/results/${resultId}`, {
    method: 'DELETE',
  });
}

export async function deleteSimulationResultsBatch(resultIds: string[]): Promise<{
  message: string;
  deleted_count: number;
  requested_count: number;
}> {
  return apiRequest('/simulation/results/delete-batch', {
    method: 'POST',
    body: JSON.stringify(resultIds),
  });
}

export async function getSimulationHistoricalContext(
  scenarioType: string = 'failure',
  affectedNodes: number = 10,
  periodHours: number = 168
): Promise<SimulationHistoricalContext> {
  const queryParams = new URLSearchParams();
  queryParams.append('scenario_type', scenarioType);
  queryParams.append('affected_nodes', affectedNodes.toString());
  queryParams.append('period_hours', periodHours.toString());

  return apiRequest(`/simulation/historical-context?${queryParams.toString()}`);
}
