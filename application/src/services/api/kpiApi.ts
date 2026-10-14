/**
 * KPI API - KPI metrics endpoints
 */

import { apiRequest } from './baseClient';

// ===== TYPES =====

export interface KPIMetricsResponse {
  total: number;
  page: number;
  page_size: number;
  items: any[];
}

export interface AggregatedKPIData {
  period: string;
  record_count: number;
  node_count: number;
  avg_ds_snr_db: number;
  avg_packet_loss_percent: number;
  avg_us_snr_db: number;
  avg_throughput: number;
  avg_latency: number;
  avg_active_modems: number;
  avg_cpu: number;
  avg_memory: number;
  avg_temperature: number;
}

export interface AggregatedKPIsResponse {
  days: number;
  granularity: string;
  start_time: string;
  end_time: string;
  data_points: number;
  items: AggregatedKPIData[];
}

// ===== FUNCTIONS =====

export async function getKPIs(params: {
  skip?: number;
  limit?: number;
  node_id?: string;
  start_time?: string;
  end_time?: string;
} = {}): Promise<KPIMetricsResponse> {
  const queryParams = new URLSearchParams();
  if (params.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params.node_id) queryParams.append('node_id', params.node_id);
  if (params.start_time) queryParams.append('start_time', params.start_time);
  if (params.end_time) queryParams.append('end_time', params.end_time);

  return apiRequest(`/kpis?${queryParams.toString()}`);
}

export async function generateKPIs(nodeIds?: string[], count: number = 100, regenerate: boolean = false): Promise<any> {
  const queryParams = new URLSearchParams();
  if (regenerate) queryParams.append('regenerate', 'true');
  const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
  return apiRequest(`/generate/kpis${query}`, {
    method: 'POST',
    body: JSON.stringify({ node_ids: nodeIds, count }),
  });
}

export async function generateHistoricalKPIs(days: number = 60, intervalMinutes: number = 60): Promise<any> {
  const queryParams = new URLSearchParams();
  queryParams.append('days', days.toString());
  queryParams.append('interval_minutes', intervalMinutes.toString());
  // Use a longer timeout for historical generation (5 minutes)
  return apiRequest(`/generate/historical-kpis?${queryParams.toString()}`, { method: 'POST' }, 300000);
}

export async function getAggregatedKPIs(params: {
  days?: number;
  granularity?: 'hourly' | 'daily';
  node_id?: string;
} = {}): Promise<AggregatedKPIsResponse> {
  const queryParams = new URLSearchParams();
  if (params.days !== undefined) queryParams.append('days', params.days.toString());
  if (params.granularity) queryParams.append('granularity', params.granularity);
  if (params.node_id) queryParams.append('node_id', params.node_id);

  return apiRequest(`/kpis/aggregated?${queryParams.toString()}`);
}
