/**
 * Config Management API - Network device configuration operations
 */

import { apiRequest } from './baseClient';
import type {
  NetworkDevice,
  ConfigChangeLog,
  ChangeRequest,
  DeviceSummary,
  ComplianceSummary,
} from '@/types';

// ===== DEVICE ENDPOINTS =====

export async function getDeviceSummary(): Promise<DeviceSummary> {
  return apiRequest('/config/devices/summary');
}

export async function getDevices(params: {
  device_type?: string;
  status?: string;
  headend_id?: string;
  hub_id?: string;
  region?: string;
  compliance_status?: string;
  skip?: number;
  limit?: number;
} = {}): Promise<{ total: number; devices: NetworkDevice[] }> {
  const qp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) qp.append(k, String(v));
  });
  const query = qp.toString() ? `?${qp.toString()}` : '';
  return apiRequest(`/config/devices${query}`);
}

export async function getDeviceDetail(deviceId: string): Promise<{
  device: NetworkDevice;
  recent_changes: ConfigChangeLog[];
  compliance_history: { compliance_id: string; compliance_status: string; severity: string; drift_count: number; scan_timestamp: string }[];
}> {
  return apiRequest(`/config/devices/${deviceId}`);
}

export async function syncDevice(deviceId: string): Promise<{ status: string; device_id: string; synced_at: string }> {
  return apiRequest(`/config/devices/${deviceId}/sync`, { method: 'POST' });
}

// ===== TEMPLATE ENDPOINTS =====

export async function getTemplates(params: {
  device_type?: string;
  device_role?: string;
} = {}): Promise<{ total: number; templates: { template_id: string; name: string; device_type: string; device_role: string }[] }> {
  const qp = new URLSearchParams();
  if (params.device_type) qp.append('device_type', params.device_type);
  if (params.device_role) qp.append('device_role', params.device_role);
  const query = qp.toString() ? `?${qp.toString()}` : '';
  return apiRequest(`/config/templates${query}`);
}

// ===== CHANGE LOG ENDPOINTS =====

export async function getChanges(params: {
  device_id?: string;
  change_type?: string;
  skip?: number;
  limit?: number;
} = {}): Promise<{ total: number; changes: ConfigChangeLog[] }> {
  const qp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) qp.append(k, String(v));
  });
  const query = qp.toString() ? `?${qp.toString()}` : '';
  return apiRequest(`/config/changes${query}`);
}

export async function rollbackChange(changeId: string): Promise<{ status: string; change_id: string }> {
  return apiRequest(`/config/changes/${changeId}/rollback`, { method: 'POST' });
}

// ===== COMPLIANCE ENDPOINTS =====

export async function getComplianceSummary(): Promise<ComplianceSummary> {
  return apiRequest('/config/compliance/summary');
}

export async function triggerComplianceScan(): Promise<{ status: string; devices_scanned: number; drifted_count: number }> {
  return apiRequest('/config/compliance/scan', { method: 'POST' });
}

// ===== CHANGE REQUEST ENDPOINTS =====

export async function getChangeRequests(params: {
  status?: string;
  skip?: number;
  limit?: number;
} = {}): Promise<{ total: number; requests: ChangeRequest[] }> {
  const qp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) qp.append(k, String(v));
  });
  const query = qp.toString() ? `?${qp.toString()}` : '';
  return apiRequest(`/config/change-requests${query}`);
}

export async function createChangeRequest(params: {
  title: string;
  description?: string;
  change_type: string;
  device_ids: string;
  requested_by?: string;
}): Promise<{ request_id: string; status: string; device_count: number }> {
  const qp = new URLSearchParams();
  qp.append('title', params.title);
  if (params.description) qp.append('description', params.description);
  qp.append('change_type', params.change_type);
  qp.append('device_ids', params.device_ids);
  if (params.requested_by) qp.append('requested_by', params.requested_by);
  return apiRequest(`/config/change-requests?${qp.toString()}`, { method: 'POST' });
}

export async function updateChangeRequest(
  requestId: string,
  params: { status?: string; reviewed_by?: string; approved_by?: string },
): Promise<{ request_id: string; status: string }> {
  const qp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v) qp.append(k, v);
  });
  return apiRequest(`/config/change-requests/${requestId}?${qp.toString()}`, { method: 'PUT' });
}

export async function executeChangeRequest(requestId: string): Promise<{
  request_id: string;
  status: string;
  execution_log: { device_id: string; status: string; change_id?: string }[];
}> {
  return apiRequest(`/config/change-requests/${requestId}/execute`, { method: 'POST' });
}
