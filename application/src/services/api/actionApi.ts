/**
 * Action API - Self-healing action endpoints
 */

import { apiRequest } from './baseClient';

// ===== TYPES =====

export interface ActionsResponse {
  total: number;
  page: number;
  page_size: number;
  items: any[];
}

// ===== FUNCTIONS =====

export async function getActions(params: {
  skip?: number;
  limit?: number;
  node_id?: string;
  action_type?: string;
  status?: string;
  since_minutes?: number;
} = {}): Promise<ActionsResponse> {
  const queryParams = new URLSearchParams();
  if (params.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params.node_id) queryParams.append('node_id', params.node_id);
  if (params.action_type) queryParams.append('action_type', params.action_type);
  if (params.status) queryParams.append('status', params.status);
  if (params.since_minutes !== undefined) queryParams.append('since_minutes', params.since_minutes.toString());

  return apiRequest(`/actions?${queryParams.toString()}`);
}

export async function cleanupOldActions(olderThanMinutes: number = 30): Promise<{ status: string; message: string; deleted: number }> {
  const queryParams = new URLSearchParams();
  queryParams.append('older_than_minutes', olderThanMinutes.toString());
  return apiRequest(`/actions/cleanup?${queryParams.toString()}`, {
    method: 'POST',
  });
}

export async function generateActions(alertIds?: string[], count: number = 20): Promise<any> {
  return apiRequest('/generate/actions', {
    method: 'POST',
    body: JSON.stringify({ alert_ids: alertIds, count }),
  });
}
