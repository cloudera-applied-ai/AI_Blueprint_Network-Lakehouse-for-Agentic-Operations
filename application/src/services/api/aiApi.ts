/**
 * AI API - AI insights, analyses, and action plan endpoints
 */

import { apiRequest } from './baseClient';

// ===== TYPES =====

export interface AIInsight {
  id: number;
  insight_id: string;
  insight_type: string;
  severity: string;
  title: string;
  description: string;
  recommendation: string;
  confidence: number;
  affected_node_ids: string[];
  related_alert_ids: string[];
  metadata?: Record<string, unknown>;
  expires_at?: string;
  created_at: string;
}

export interface AIInsightsResponse {
  total: number;
  items: AIInsight[];
  generated_at: string;
}

export interface AIAnalysis {
  alert_id: string;
  node_id: string;
  summary: string;
  root_cause: string;
  recommendations: string[];
  confidence: number;
  reasoning?: string;
  should_execute_autonomously: boolean;
  urgency_score: number;
  sensor_data_used?: Record<string, unknown>;
  analysis_time_ms?: number;
}

export interface AIAnalysisListResponse {
  total: number;
  items: AIAnalysis[];
}

export interface AIActionStep {
  step_number: number;
  action_type: string;
  description: string;
  parameters?: Record<string, unknown>;
  estimated_duration_seconds: number;
  status: string;
  started_at?: string;
  completed_at?: string;
  result?: string;
}

export interface AIActionPlan {
  id: number;
  plan_id: string;
  alert_id: string;
  node_id: string;
  analysis_id?: string;
  root_cause: string;
  priority: string;
  status: string;
  steps: AIActionStep[];
  current_step_index: number;
  started_at?: string;
  completed_at?: string;
  execution_log?: Record<string, unknown>[];
  failure_reason?: string;
  success?: boolean;
  created_actions?: string[];
  created_at: string;
  updated_at?: string;
}

export interface AIActionPlanListResponse {
  total: number;
  items: AIActionPlan[];
}

export interface AnalyzeAndExecuteResponse {
  analysis: AIAnalysis;
  plan?: AIActionPlan;
  executed: boolean;
}

export interface AIStatus {
  enabled: boolean;
  llm_enabled: boolean;
  insights_count: number;
  insights_last_generated?: string;
  insights_expires_at?: string;
  active_analyses: number;
  pending_plans: number;
  executing_plans: number;
  completed_plans_24h: number;
  failed_plans_24h: number;
  timestamp: string;
}

// ===== FUNCTIONS =====

export async function getAIInsights(params: {
  severity?: string;
  insight_type?: string;
  node_id?: string;
  limit?: number;
  regenerate?: boolean;
} = {}): Promise<AIInsightsResponse> {
  const queryParams = new URLSearchParams();
  if (params.severity) queryParams.append('severity', params.severity);
  if (params.insight_type) queryParams.append('insight_type', params.insight_type);
  if (params.node_id) queryParams.append('node_id', params.node_id);
  if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params.regenerate) queryParams.append('regenerate', 'true');

  // AI insights can take longer due to rule-based analysis, use 90s timeout
  return apiRequest(`/ai/insights?${queryParams.toString()}`, {}, 90000);
}

export async function triggerAIAnalysis(
  alertId: string,
  useLLM: boolean = true
): Promise<AIAnalysis> {
  const queryParams = new URLSearchParams();
  queryParams.append('use_llm', String(useLLM));
  return apiRequest(`/ai/analyze/${alertId}?${queryParams.toString()}`, {
    method: 'POST',
  });
}

export async function getAIAnalyses(params: {
  skip?: number;
  limit?: number;
  alert_id?: string;
  node_id?: string;
  autonomous_only?: boolean;
} = {}): Promise<AIAnalysisListResponse> {
  const queryParams = new URLSearchParams();
  if (params.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params.alert_id) queryParams.append('alert_id', params.alert_id);
  if (params.node_id) queryParams.append('node_id', params.node_id);
  if (params.autonomous_only) queryParams.append('autonomous_only', 'true');

  return apiRequest(`/ai/analyses?${queryParams.toString()}`);
}

export async function getAIActionPlans(params: {
  skip?: number;
  limit?: number;
  status?: string;
  node_id?: string;
  priority?: string;
} = {}): Promise<AIActionPlanListResponse> {
  const queryParams = new URLSearchParams();
  if (params.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params.status) queryParams.append('status', params.status);
  if (params.node_id) queryParams.append('node_id', params.node_id);
  if (params.priority) queryParams.append('priority', params.priority);

  return apiRequest(`/ai/plans?${queryParams.toString()}`);
}

export async function getAIActionPlan(planId: string): Promise<AIActionPlan> {
  return apiRequest(`/ai/plans/${planId}`);
}

export async function cancelAIActionPlan(planId: string): Promise<{ message: string; status: string }> {
  return apiRequest(`/ai/plans/${planId}/cancel`, { method: 'POST' });
}

export async function analyzeAndExecuteAlert(
  alertId: string,
  execute: boolean = true
): Promise<AnalyzeAndExecuteResponse> {
  const queryParams = new URLSearchParams();
  queryParams.append('execute', String(execute));
  return apiRequest(`/ai/analyze-and-execute/${alertId}?${queryParams.toString()}`, {
    method: 'POST',
  }, 120000);  // 2 minute timeout for analysis + execution
}

export async function getAIStatus(): Promise<AIStatus> {
  return apiRequest('/ai/status');
}
