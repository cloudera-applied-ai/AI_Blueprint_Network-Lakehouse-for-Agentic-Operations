/**
 * System API - Health, stats, system status and control endpoints
 */

import { apiRequest, getApiBaseUrl } from './baseClient';

// ===== TYPES =====

export interface StatsResponse {
  nodes: number;
  kpi_metrics: number;
  alerts: number;
  actions: number;
  timestamp: string;
}

interface HealthCheckResponse {
  status: string;
  ready: boolean;
  startup_complete?: boolean;
  data_ready?: boolean;
  timestamp: string;
}

export interface SystemStatus {
  data_generation: {
    running: boolean;
    paused: boolean;
    stats: {
      kpis_generated: number;
      alerts_generated: number;
      actions_generated: number;
      last_run: string | null;
      cycles: number;
      skipped_cycles: number;
    };
  };
  llm: {
    paused: boolean;
  };
  timestamp: string;
}

// ===== FUNCTIONS =====

export async function getStats(): Promise<StatsResponse> {
  return apiRequest('/stats');
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const controller = new AbortController();
    // 5-second timeout — container/Docker environments can be slow on first request
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(`${getApiBaseUrl()}/health`, {
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      return false;
    }

    // Check if backend is fully ready (startup complete AND data loaded)
    const health: HealthCheckResponse = await response.json();
    return health.ready === true;
  } catch (error) {
    // Don't log abort errors - they're expected when backend is slow/unavailable
    if (!(error instanceof Error && error.name === 'AbortError')) {
      console.error('Backend health check failed:', error);
    }
    return false;
  }
}

export async function getSystemStatus(): Promise<SystemStatus> {
  return apiRequest('/system/status');
}

export async function pauseSystem(options: {
  dataGeneration?: boolean;
  llm?: boolean;
} = { dataGeneration: true, llm: true }): Promise<{ status: string; paused: Record<string, string>; timestamp: string }> {
  const params = new URLSearchParams();
  if (options.dataGeneration !== undefined) params.append('data_generation', String(options.dataGeneration));
  if (options.llm !== undefined) params.append('llm', String(options.llm));

  return apiRequest(`/system/pause?${params.toString()}`, { method: 'POST' });
}

export async function resumeSystem(options: {
  dataGeneration?: boolean;
  llm?: boolean;
} = { dataGeneration: true, llm: true }): Promise<{ status: string; resumed: Record<string, string>; timestamp: string }> {
  const params = new URLSearchParams();
  if (options.dataGeneration !== undefined) params.append('data_generation', String(options.dataGeneration));
  if (options.llm !== undefined) params.append('llm', String(options.llm));

  return apiRequest(`/system/resume?${params.toString()}`, { method: 'POST' });
}

export async function isLLMPaused(): Promise<boolean> {
  try {
    const response = await apiRequest<{ paused: boolean }>('/system/llm-paused');
    return response.paused;
  } catch {
    return false; // Default to not paused if backend unavailable
  }
}
