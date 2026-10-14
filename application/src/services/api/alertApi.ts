/**
 * Alert API - Alert endpoints
 */

import { apiRequest } from './baseClient';

// ===== TYPES =====

export interface AlertsResponse {
  total: number;
  page: number;
  page_size: number;
  items: any[];
}

// ===== FUNCTIONS =====

export async function getAlerts(params: {
  skip?: number;
  limit?: number;
  node_id?: string;
  severity?: string;
  status?: string;
  start_time?: string;
} = {}): Promise<AlertsResponse> {
  const queryParams = new URLSearchParams();
  if (params.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params.node_id) queryParams.append('node_id', params.node_id);
  if (params.severity) queryParams.append('severity', params.severity);
  if (params.status) queryParams.append('status', params.status);
  if (params.start_time) queryParams.append('start_time', params.start_time);

  return apiRequest(`/alerts?${queryParams.toString()}`);
}

export async function generateAlerts(nodeIds?: string[], count: number = 50): Promise<any> {
  return apiRequest('/generate/alerts', {
    method: 'POST',
    body: JSON.stringify({ node_ids: nodeIds, count }),
  });
}
