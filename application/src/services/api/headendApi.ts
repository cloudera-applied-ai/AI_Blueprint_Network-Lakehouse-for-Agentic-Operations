/**
 * Headend API - Headend endpoints
 */

import { apiRequest } from './baseClient';

// ===== TYPES =====

export interface HeadendResponse {
  headend_id: string;
  name: string;
  region: string;
  city: string;
  status: string;
  tier: string;
  location?: string;
  country?: string;
  power_capacity_mw?: number;
  current_power_mw?: number;
  total_rack_units?: number;
  used_rack_units?: number;
}

export interface HeadendMetadataSummary {
  total_headends: number;
  regions: { value: string; count: number }[];
  cities: { value: string; count: number; region: string }[];
  statuses: { value: string; count: number }[];
}

// ===== FUNCTIONS =====

export async function getHeadends(params: {
  region?: string;
  city?: string;
  status?: string;
  skip?: number;
  limit?: number;
} = {}): Promise<{ items: HeadendResponse[]; total: number }> {
  const queryParams = new URLSearchParams();
  if (params.region) queryParams.append('region', params.region);
  if (params.city) queryParams.append('city', params.city);
  if (params.status) queryParams.append('status', params.status);
  if (params.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());

  return apiRequest(`/headends?${queryParams.toString()}`);
}

export async function getHeadendMetadataSummary(): Promise<HeadendMetadataSummary> {
  return apiRequest('/headends/metadata/summary');
}
