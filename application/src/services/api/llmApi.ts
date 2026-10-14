/**
 * LLM API - LLM configuration CRUD endpoints
 */

import { apiRequest } from './baseClient';

// ===== TYPES =====

export interface LLMConfig {
  id: number;
  config_key: string;
  provider: string;
  endpoint_url?: string;
  api_key?: string;
  jwt_token?: string;
  jwt_token_expires?: string;
  model_name?: string;
  writer_model_name?: string;
  writer_provider?: string;
  writer_endpoint_url?: string;
  writer_api_key?: string;
  temperature: number;
  max_tokens: number;
  enabled: boolean;
  created_at: string;
  updated_at?: string;
}

// Clearable fields accept null: the backend applies saves with exclude_unset,
// so `null` explicitly clears a field while omitting it leaves it untouched
// (jwt_token is deliberately never sent by the UI so saves can't wipe it).
export interface LLMConfigCreate {
  provider: string;
  endpoint_url?: string | null;
  api_key?: string | null;
  jwt_token?: string | null;
  jwt_token_expires?: string | null;
  model_name?: string | null;
  writer_model_name?: string | null;
  writer_provider?: string | null;
  writer_endpoint_url?: string | null;
  writer_api_key?: string | null;
  temperature?: number;
  max_tokens?: number;
  enabled?: boolean;
}

export interface LLMConfigUpdate {
  provider?: string;
  endpoint_url?: string | null;
  api_key?: string | null;
  jwt_token?: string | null;
  jwt_token_expires?: string | null;
  model_name?: string | null;
  writer_model_name?: string | null;
  writer_provider?: string | null;
  writer_endpoint_url?: string | null;
  writer_api_key?: string | null;
  temperature?: number;
  max_tokens?: number;
  enabled?: boolean;
}

// ===== FUNCTIONS =====

export async function getLLMConfig(): Promise<LLMConfig> {
  return apiRequest('/llm/config');
}

export async function createOrUpdateLLMConfig(config: LLMConfigCreate): Promise<LLMConfig> {
  return apiRequest('/llm/config', {
    method: 'POST',
    body: JSON.stringify(config),
  });
}

export async function updateLLMConfig(config: LLMConfigUpdate): Promise<LLMConfig> {
  return apiRequest('/llm/config', {
    method: 'PATCH',
    body: JSON.stringify(config),
  });
}

export async function deleteLLMConfig(): Promise<{ status: string; message: string }> {
  return apiRequest('/llm/config', {
    method: 'DELETE',
  });
}

export interface LLMTestResult {
  ok: boolean;
  message: string;
}

/**
 * Probe the configured LLM through the backend's real request path
 * (queue + provider handling). role="writer" exercises the writer model's
 * endpoint/auth so a broken two-model config is caught in Settings.
 */
export async function testBackendLLMConnection(
  role: 'analyst' | 'writer' = 'analyst'
): Promise<LLMTestResult> {
  return apiRequest('/llm/test-connection', {
    method: 'POST',
    body: JSON.stringify({ role }),
  });
}
