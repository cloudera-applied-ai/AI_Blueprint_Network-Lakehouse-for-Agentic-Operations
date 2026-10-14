/**
 * Base API Client - Core functionality for all API modules
 * Features: request deduplication, timeout handling, error handling
 */

import { systemSettingsService } from '../systemSettingsService';

/**
 * Get the current API base URL (either from system settings or .env fallback)
 */
export function getApiBaseUrl(): string {
  return systemSettingsService.getBackendUrl();
}

/**
 * Get the API key for authenticating backend requests.
 */
function getApiKey(): string | undefined {
  return import.meta.env.VITE_API_KEY || 'dev-api-key-change-me';
}

// In-flight request cache for deduplication
const inFlightRequests = new Map<string, Promise<unknown>>();

/**
 * Generic API request handler with error handling, timeout, and deduplication
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
  timeout: number = 30000 // 30 second default timeout
): Promise<T> {
  const method = options.method || 'GET';
  const cacheKey = `${method}:${endpoint}`;

  // For GET requests, deduplicate by returning existing promise if in flight
  if (method === 'GET') {
    const existingPromise = inFlightRequests.get(cacheKey);
    if (existingPromise) {
      return existingPromise as Promise<T>;
    }
  }

  const requestPromise = (async (): Promise<T> => {
    try {
      const API_V1 = `${getApiBaseUrl()}/api/v1`;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const apiKey = getApiKey();
      const response = await fetch(`${API_V1}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(apiKey ? { 'X-API-Key': apiKey } : {}),
          ...options.headers,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `API Error: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Request timeout after ${timeout / 1000} seconds for: ${endpoint}`);
      }
      // Ensure we have a proper error message
      let errorMessage: string;
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      } else if (error && typeof error === 'object' && 'message' in error) {
        errorMessage = String((error as { message: unknown }).message);
      } else {
        errorMessage = JSON.stringify(error);
      }
      console.error(`API request failed: ${endpoint}`, errorMessage);
      throw new Error(errorMessage);
    } finally {
      // Clean up after request completes (success or failure)
      inFlightRequests.delete(cacheKey);
    }
  })();

  // Only cache GET requests
  if (method === 'GET') {
    inFlightRequests.set(cacheKey, requestPromise);
  }

  return requestPromise;
}

// Generic API client object for flexible endpoint access
export const apiClient = {
  async get<T>(endpoint: string): Promise<T> {
    return apiRequest<T>(endpoint);
  },
  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return apiRequest<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  },
  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return apiRequest<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  },
  async delete<T>(endpoint: string): Promise<T> {
    return apiRequest<T>(endpoint, { method: 'DELETE' });
  },
};
