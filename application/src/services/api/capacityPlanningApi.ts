/**
 * Capacity Planning API - Agentic capacity planning endpoints
 */

import { apiRequest } from './baseClient';

// ===== TYPES =====

export interface CapacityForecast {
  period_days: number;
  projected_node_utilization: number;
  projected_dc_utilization: number;
  projected_bandwidth_usage_gbps: number;
  confidence: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
}

export interface BandwidthBottleneck {
  location: string;
  current_utilization: number;
  projected_breach_days: number | null;
}

export interface CapacityConstraint {
  resource: 'cpu' | 'memory' | 'bandwidth' | 'storage';
  affected_components: string[];
  severity: 'low' | 'medium' | 'high';
}

export interface AgentThought {
  id: string;
  timestamp: string;
  agent_id: string;
  agent_name: string;
  type: string;  // thought, action, tool_call, tool_result, data, analysis, error
  content: string;
  progress_percent?: number;
  data_summary?: Record<string, unknown>;
}

export interface UpgradeImpactAnalysis {
  nodes_analyzed: number;
  current_total_bandwidth_gbps: number;
  projected_total_bandwidth_gbps: number;
  bandwidth_improvement_percent: number;
  current_avg_latency_ms: number;
  projected_avg_latency_ms: number;
  latency_improvement_percent: number;
  nodes_by_current_backhaul: Record<string, number>;
  upgrade_target: string;
  users_to_benefit: number;
}

export interface HardwareCompatibilityReport {
  total_nodes_checked: number;
  compatible_count: number;
  partial_upgrade_count: number;
  replacement_count: number;
  compatibility_by_manufacturer: Record<string, Record<string, number>>;
  estimated_total_cost: number;
  estimated_upgrade_cost: number;
  estimated_replacement_cost: number;
  cost_breakdown_by_manufacturer: Record<string, number>;
  installation_timeline_days: number;
}

export interface AgenticCapacityPlanningRequest {
  analysis_mode: 'current_state' | 'upgrade_scenario' | 'add_redundancy';
  target_upgrade_type?: 'Fiber' | 'Starlink' | 'Microwave';
  current_node_type_filter?: string[];
  region?: string;
  city?: string;
  datacenter_ids?: string[];
  node_ids?: string[];
  forecast_periods?: number[];
  include_cost_estimate?: boolean;
}

export interface AgenticCapacityPlanningStartResponse {
  execution_id: string;
  status: string;
}

export interface DatacenterComponentStatus {
  component_id: string;
  component_type: string;
  name?: string;
  location?: string;
  region?: string;
  utilization_percent: number;
  status: string;
  health_score: number;
  trend_7d: string;
  trend_30d: string;
  recommendations: string[];
  estimated_upgrade_cost?: number;
}

export interface SiteAnalysis {
  dc_id: string;
  name: string;
  city: string;
  status: string;
  total_components: number;
  components_by_type: Record<string, number>;
  health_score: number;
  critical_count: number;
  high_count: number;
  issues: string[];
  power_capacity_mw: number;
  current_power_mw: number;
  power_utilization_percent: number;
  total_rack_units: number;
  used_rack_units: number;
  rack_utilization_percent: number;
  avg_growth_per_week: number;
  recommendations: string[];
}

export interface DatacenterAnalysis {
  datacenter_id?: string;
  datacenter_name?: string;
  total_components: number;
  overall_health_score: number;  // Backend uses overall_health_score
  critical_issues: string[];     // Array of issue descriptions
  estimated_total_upgrade_cost: number;
  components_by_type: Record<string, number>;
  components: DatacenterComponentStatus[];
  upgrade_recommendations: UpgradeRecommendation[];  // Backend uses upgrade_recommendations
  priority_upgrades: string[];
  // Site-level breakdown
  sites?: SiteAnalysis[];
  // Regional breakdown
  issues_by_location?: Record<string, string[]>;
  components_by_location?: Record<string, number>;
  health_by_location?: Record<string, number>;
  growth_by_location?: Record<string, {
    avg_growth_per_week: number;
    avg_growth_per_month: number;
    critical_count: number;
    high_count: number;
  }>;
}

export interface UpgradeRecommendation {
  component_id: string;
  component_type: string;
  name: string;
  priority: string;
  issues: string[];
  current_utilization: number;
  growth_trend?: number;
  estimated_cost: number;
  recommendation: string;
}

export interface DatacenterForecastPeriod {
  period_days: number;
  projected_power_util: number;
  projected_rack_util: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
}

export interface DatacenterForecast {
  dc_id: string;
  dc_name: string;
  city: string;
  current_power_util: number;
  current_rack_util: number;
  health_score: number;
  growth_rate_per_month: number;
  forecasts: DatacenterForecastPeriod[];
}

export interface AgenticCapacityPlanningStatus {
  execution_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  current_agent?: string;
  current_agent_name?: string;
  progress_percent: number;
  thoughts: AgentThought[];
  analysis_mode: string;
  target_backhaul_type?: string;
  upgrade_analysis?: UpgradeImpactAnalysis;
  hardware_compatibility?: HardwareCompatibilityReport;
  datacenter_analysis?: DatacenterAnalysis;
  result?: {
    trend_direction?: string;
    growth_rate_percent_per_month?: number;
    current_node_utilization?: number;
    current_dc_utilization?: number;
    total_throughput_gbps?: number;
    forecasts?: CapacityForecast[];
    datacenter_forecasts?: DatacenterForecast[];
    bandwidth_bottlenecks?: BandwidthBottleneck[];
    capacity_constraints?: CapacityConstraint[];
    analysis_summary?: string;
    recommendations?: string[];
    upgrade_impact?: UpgradeImpactAnalysis;
    hardware_compatibility?: HardwareCompatibilityReport;
  };
  error?: string;
}

// ===== FUNCTIONS =====

export async function startAgenticCapacityPlanning(
  request: AgenticCapacityPlanningRequest
): Promise<AgenticCapacityPlanningStartResponse> {
  return apiRequest('/capacity-planning/agentic/start', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getAgenticCapacityPlanningStatus(
  executionId: string
): Promise<AgenticCapacityPlanningStatus> {
  return apiRequest(`/capacity-planning/agentic/${executionId}`);
}
