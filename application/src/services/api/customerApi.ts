/**
 * Customer Intelligence API - Customer accounts, sentiment, and plan analytics
 */

import { apiRequest } from './baseClient';

// ===== TYPES =====

export interface CustomerOverview {
  total_customers: number;
  total_active: number;
  total_monthly_revenue: number;
  avg_sentiment_score: number;
  avg_nps_score: number;
  total_sentiments: number;
  by_service_plan: Record<string, {
    total: number;
    active: number;
    suspended: number;
    closed: number;
    revenue: number;
  }>;
  by_docsis_version: Record<string, number>;
  connection_quality: {
    high_drop_customers: number;
    meeting_speed_threshold: number;
    below_speed_threshold: number;
  };
}

export interface CustomerRecord {
  account_id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  node_id: string;
  service_plan: string;
  monthly_rate: number;
  modem_manufacturer: string;
  modem_model: string;
  docsis_version: string;
  provisioned_download_mbps: number;
  actual_download_mbps: number;
  provisioned_upload_mbps: number;
  actual_upload_mbps: number;
  connection_drops_24h: number;
  drop_quality: string;
  account_status: string;
  contract_status: string;
  tenure_months: number;
  avg_sentiment_score: number | null;
}

export interface CustomerListResponse {
  total: number;
  customers: CustomerRecord[];
}

export interface SentimentSourceEntry {
  source: string;
  count: number;
  avg_score: number;
}

export interface SentimentSummary {
  by_source: SentimentSourceEntry[];
  by_label: Record<string, number>;
  nps: {
    score: number;
    promoters: number;
    passives: number;
    detractors: number;
    total_responses: number;
  };
  by_resolution: Record<string, number>;
}

export interface PlanDetail {
  plan: string;
  total: number;
  active: number;
  suspended: number;
  closed: number;
  churn_risk_pct: number;
  monthly_revenue: number;
  avg_tenure_months: number;
  avg_download_mbps: number;
  provisioned_download_mbps: number;
  speed_compliant: number;
  speed_compliance_pct: number;
}

export interface PlanBreakdown {
  plans: PlanDetail[];
}

// ===== FUNCTIONS =====

export async function getCustomerOverview(region?: string): Promise<CustomerOverview> {
  const params = new URLSearchParams();
  if (region) params.append('region', region);
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiRequest(`/customers/overview${query}`);
}

export async function getCustomerList(opts: {
  skip?: number;
  limit?: number;
  service_plan?: string;
  account_status?: string;
  search?: string;
  node_id?: string;
  region?: string;
} = {}): Promise<CustomerListResponse> {
  const params = new URLSearchParams();
  if (opts.skip !== undefined) params.append('skip', String(opts.skip));
  if (opts.limit !== undefined) params.append('limit', String(opts.limit));
  if (opts.service_plan) params.append('service_plan', opts.service_plan);
  if (opts.account_status) params.append('account_status', opts.account_status);
  if (opts.search) params.append('search', opts.search);
  if (opts.node_id) params.append('node_id', opts.node_id);
  if (opts.region) params.append('region', opts.region);
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiRequest(`/customers/list${query}`);
}

export async function getSentimentSummary(region?: string): Promise<SentimentSummary> {
  const params = new URLSearchParams();
  if (region) params.append('region', region);
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiRequest(`/customers/sentiment/summary${query}`);
}

export async function getPlanBreakdown(region?: string): Promise<PlanBreakdown> {
  const params = new URLSearchParams();
  if (region) params.append('region', region);
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiRequest(`/customers/plans/breakdown${query}`);
}
