/**
 * Node API - Fiber Node CRUD operations and metadata
 */

import { apiRequest } from './baseClient';

// ===== TYPES =====

export interface FiberNodeResponse {
  total: number;
  page: number;
  page_size: number;
  items: any[];
}

export interface NodeMetadataSummary {
  total_nodes: number;
  node_types: { value: string; count: number }[];
  docsis_versions: { value: string; count: number }[];
  regions: { value: string; count: number }[];
  statuses: { value: string; count: number }[];
}

// ===== FUNCTIONS =====

export async function getNodes(params: {
  skip?: number;
  limit?: number;
  region?: string;
  status?: string;
  manufacturer?: string;
} = {}): Promise<FiberNodeResponse> {
  const queryParams = new URLSearchParams();
  if (params.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params.region) queryParams.append('region', params.region);
  if (params.status) queryParams.append('status', params.status);
  if (params.manufacturer) queryParams.append('manufacturer', params.manufacturer);

  return apiRequest(`/nodes?${queryParams.toString()}`);
}

export async function getNodeById(nodeId: string): Promise<any> {
  return apiRequest(`/nodes/${nodeId}`);
}

export async function getNodeMetadataSummary(): Promise<NodeMetadataSummary> {
  return apiRequest('/nodes/metadata/summary');
}

export async function generateNodes(count: number = 1000, region?: string, regenerate: boolean = false): Promise<any> {
  const queryParams = new URLSearchParams();
  if (regenerate) queryParams.append('regenerate', 'true');
  const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
  return apiRequest(`/generate/nodes${query}`, {
    method: 'POST',
    body: JSON.stringify({ count, region }),
  });
}
