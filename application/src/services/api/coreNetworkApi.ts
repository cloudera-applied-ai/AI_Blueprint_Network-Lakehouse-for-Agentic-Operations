/**
 * Core Network API - Headend, Hub, and infrastructure operations
 */

import { apiRequest } from './baseClient';

// ===== TYPES =====

export interface Headend {
  headend_id: string;
  name: string;
  region: string;
  service_area: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  cmts_count: number;
  total_cmts_ports: number;
  active_cmts_ports: number;
  port_utilization_percent: number;
  video_server_count: number;
  core_router_count: number;
  peering_capacity_gbps: number;
  total_rack_units: number;
  power_capacity_mw: number;
  total_homes_served: number;
  total_active_subscribers: number;
  status: string;
}

export interface HeadendsResponse {
  total: number;
  headends: Headend[];
}

export interface Hub {
  hub_id: string;
  headend_id: string;
  name: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  fiber_nodes_served: number;
  total_homes_served: number;
  fiber_capacity_gbps: number;
  current_throughput_gbps: number;
  utilization_percent: number;
  power_status: string;
  battery_backup_hours: number;
  status: string;
}

export interface HubsResponse {
  total: number;
  hubs: Hub[];
}

export interface Amplifier {
  amp_id: string;
  node_id: string;
  manufacturer: string;
  model: string;
  amp_type: string;
  cascade_position: number;
  location_type: string;
  ds_input_level: number;
  ds_output_level: number;
  us_input_level: number;
  us_output_level: number;
  ds_snr: number;
  us_snr: number;
  temperature_celsius: number;
  power_consumption_watts: number;
  power_supply_status: string;
  status: string;
}

export interface AmplifiersResponse {
  total: number;
  amplifiers: Amplifier[];
}

export interface NetworkDevice {
  device_id: string;
  device_type: string;
  device_role: string;
  hostname: string;
  headend_id: string | null;
  hub_id: string | null;
  region: string | null;
  manufacturer: string;
  hardware_model: string;
  firmware_version: string;
  management_ip: string;
  uplink_speed_gbps: number;
  status: string;
  compliance_status: string;
  cpu_utilization: number;
  memory_utilization: number;
  temperature_celsius: number;
}

export interface NetworkDevicesResponse {
  total: number;
  devices: NetworkDevice[];
}

// ===== FUNCTIONS =====

export async function getHeadends(region?: string): Promise<HeadendsResponse> {
  const params = new URLSearchParams();
  if (region) params.append('region', region);
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiRequest(`/core-network/headends${query}`);
}

export async function getHubs(params: {
  region?: string;
  headend_id?: string;
} = {}): Promise<HubsResponse> {
  const queryParams = new URLSearchParams();
  if (params.region) queryParams.append('region', params.region);
  if (params.headend_id) queryParams.append('headend_id', params.headend_id);
  const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
  return apiRequest(`/core-network/hubs${query}`);
}

export async function getAmplifiers(params: {
  node_id?: string;
  region?: string;
  skip?: number;
  limit?: number;
} = {}): Promise<AmplifiersResponse> {
  const queryParams = new URLSearchParams();
  if (params.node_id) queryParams.append('node_id', params.node_id);
  if (params.region) queryParams.append('region', params.region);
  if (params.skip !== undefined) queryParams.append('skip', String(params.skip));
  if (params.limit !== undefined) queryParams.append('limit', String(params.limit));
  const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
  return apiRequest(`/core-network/amplifiers${query}`);
}

export async function getNetworkDevices(params: {
  device_type?: string;
  headend_id?: string;
  hub_id?: string;
  region?: string;
  skip?: number;
  limit?: number;
} = {}): Promise<NetworkDevicesResponse> {
  const queryParams = new URLSearchParams();
  if (params.device_type) queryParams.append('device_type', params.device_type);
  if (params.headend_id) queryParams.append('headend_id', params.headend_id);
  if (params.hub_id) queryParams.append('hub_id', params.hub_id);
  if (params.region) queryParams.append('region', params.region);
  if (params.skip !== undefined) queryParams.append('skip', String(params.skip));
  if (params.limit !== undefined) queryParams.append('limit', String(params.limit));
  const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
  return apiRequest(`/core-network/network-devices${query}`);
}
