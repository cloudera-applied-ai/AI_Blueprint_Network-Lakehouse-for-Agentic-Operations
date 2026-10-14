/**
 * LLM Service - Handles communication with LLM providers
 * Supports OpenAI, Anthropic, Cloudera, and custom endpoints
 * Now with backend API integration for shared configuration
 */

import { LLMConfig, LLMMessage, LLMResponse, LLMProvider } from '@/types/llm';
import {
  getLLMConfig as getBackendLLMConfig,
  createOrUpdateLLMConfig,
} from './apiClient';
import { systemSettingsService } from './systemSettingsService';

/** Get headers for backend API requests including API key auth */
function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const apiKey = import.meta.env.VITE_API_KEY || 'dev-api-key-change-me';
  headers['X-API-Key'] = apiKey;
  return headers;
}

class LLMService {
  private config: LLMConfig | null = null;
  private jwtToken: string | null = null;
  private tokenRefreshInterval: NodeJS.Timeout | null = null;
  public lastError: string = '';

  // Rate limiting: max concurrent requests and minimum delay between requests
  // OPTIMIZED: More aggressive rate limiting for GPU relief
  private activeRequests: number = 0;
  private readonly maxConcurrentRequests: number = 1; // Reduced from 2 to 1 for GPU optimization
  private lastRequestTime: number = 0;
  private readonly minRequestInterval: number = 2000; // Increased from 1s to 2s between requests

  /**
   * Initialize LLM service with configuration
   * Note: Does NOT test connection - use testConnection() separately to avoid circular calls
   */
  async initialize(config: LLMConfig): Promise<boolean> {
    // Make a deep copy to avoid modifying the original config object
    this.config = { ...config };
    this.lastError = '';

    if (!this.config.enabled) {
      console.log('LLM service disabled');
      return false;
    }

    // Try to load JWT token if path provided
    if (this.config.jwtTokenPath) {
      await this.loadJWTToken(this.config.jwtTokenPath);
      // Refresh token every 30 minutes
      this.startTokenRefresh(this.config.jwtTokenPath);
    }

    // Validate configuration (but don't test connection - that's done separately)
    const validationError = await this.validateConfig();
    if (validationError) {
      this.lastError = validationError;
      console.warn('Invalid LLM configuration:', validationError);
      this.config.enabled = false;
      return false;
    }

    console.log(`LLM service initialized with provider: ${config.provider}`);
    return true;
  }

  /**
   * Load JWT token from file system
   */
  private async loadJWTToken(_path: string): Promise<void> {
    try {
      // In browser environment, we can't directly read files
      // This would need to be handled by a backend service
      // For now, we'll check if there's a token in localStorage as a workaround
      const storedToken = localStorage.getItem('llm_jwt_token');
      if (storedToken) {
        this.jwtToken = storedToken;
        console.log('JWT token loaded from storage');
      }
      // Silent fallback to API key - no warning needed
    } catch (error) {
      console.error('Error loading JWT token:', error);
    }
  }

  /**
   * Start automatic token refresh
   */
  private startTokenRefresh(path: string): void {
    if (this.tokenRefreshInterval) {
      clearInterval(this.tokenRefreshInterval);
    }

    this.tokenRefreshInterval = setInterval(() => {
      this.loadJWTToken(path);
    }, 30 * 60 * 1000); // 30 minutes
  }

  /**
   * Stop automatic token refresh
   */
  stopTokenRefresh(): void {
    if (this.tokenRefreshInterval) {
      clearInterval(this.tokenRefreshInterval);
      this.tokenRefreshInterval = null;
    }
  }

  /**
   * Validate LLM configuration
   * Returns error message if invalid, empty string if valid
   */
  private async validateConfig(): Promise<string> {
    if (!this.config) return 'Configuration is missing';

    // Check required fields
    if (!this.config.endpoint) {
      return 'Endpoint URL is required';
    }

    if (!this.config.model) {
      return 'Model name is required';
    }

    // Check authentication (Ollama runs locally without auth)
    if (this.config.provider !== 'ollama' && !this.jwtToken && !this.config.apiKey) {
      return 'API Key is required (or JWT token must be configured)';
    }

    return '';  // Valid
  }

  /**
   * Wait for rate limiting - returns true if request should proceed, false if should be skipped
   */
  private async waitForRateLimit(priority: boolean = false): Promise<boolean> {
    // Priority requests (like test connection) skip rate limiting
    if (priority) {
      return true;
    }

    // Check if we have too many concurrent requests
    if (this.activeRequests >= this.maxConcurrentRequests) {
      console.log(`⏳ Rate limited: ${this.activeRequests} active requests (max ${this.maxConcurrentRequests}), skipping request`);
      return false;
    }

    // Enforce minimum delay between requests
    const now = Date.now();
    const timeSinceLastRequest = now - this.lastRequestTime;
    if (timeSinceLastRequest < this.minRequestInterval) {
      const waitTime = this.minRequestInterval - timeSinceLastRequest;
      console.log(`⏳ Rate limiting: waiting ${waitTime}ms before next request`);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }

    return true;
  }

  /**
   * Send completion request to LLM
   * @param messages - Messages to send
   * @param forceRequest - If true, skips the enabled check (used for testing connection)
   * @param timeout - Request timeout in milliseconds (default 60s)
   * @param priority - If true, bypasses rate limiting (used for test connections)
   */
  async complete(messages: LLMMessage[], forceRequest: boolean = false, timeout: number = 60000, priority: boolean = false): Promise<LLMResponse | null> {
    if (!this.config) {
      console.log('❌ LLM complete: No config');
      return null;
    }

    if (!forceRequest && !this.config.enabled) {
      console.log('❌ LLM complete: Service disabled');
      return null;
    }

    // Apply rate limiting (unless priority)
    const shouldProceed = await this.waitForRateLimit(priority || forceRequest);
    if (!shouldProceed) {
      return null;
    }

    this.activeRequests++;
    this.lastRequestTime = Date.now();

    try {
      // Call backend proxy instead of making direct API calls
      // This keeps API keys secure and centralizes LLM calls
      const backendUrl = systemSettingsService.getBackendUrl();
      const endpoint = `${backendUrl}/api/v1/llm/complete`;
      console.log(`📤 Sending LLM request to: ${endpoint} (active: ${this.activeRequests})`);

      // Add AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ messages }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      console.log(`📥 LLM response status: ${response.status}`);

      if (!response.ok) {
        const errorText = await response.text();
        this.lastError = `Backend LLM proxy error: HTTP ${response.status}: ${errorText}`;
        console.error(`❌ LLM error: ${this.lastError}`);
        return null;
      }

      const data = await response.json();
      console.log('📥 LLM response data:', data);
      // Parse the response from the backend (which already formats it from the LLM)
      return this.parseResponse(data);
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        this.lastError = `LLM request timed out after ${timeout / 1000} seconds`;
        console.error(`❌ LLM timeout: ${this.lastError}`);
      } else {
        this.lastError = error instanceof Error ? error.message : String(error);
        console.error(`❌ LLM fetch error: ${this.lastError}`);
      }
      return null;
    } finally {
      this.activeRequests--;
    }
  }

  /**
   * Submit LLM request to backend queue (async, non-blocking)
   * Returns a job ID that can be used to poll for results
   * Use this for batch processing or when you don't need immediate results
   */
  async submitToQueue(messages: LLMMessage[], priority: number = 0): Promise<string | null> {
    if (!this.config) {
      console.log('❌ LLM submitToQueue: No config');
      return null;
    }

    if (!this.config.enabled) {
      console.log('❌ LLM submitToQueue: Service disabled');
      return null;
    }

    try {
      const backendUrl = systemSettingsService.getBackendUrl();
      const endpoint = `${backendUrl}/api/v1/llm/queue/submit`;
      console.log(`📤 Submitting LLM request to queue: ${endpoint}`);

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ messages, priority }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        this.lastError = `Queue submit error: HTTP ${response.status}: ${errorText}`;
        console.error(`❌ Queue submit error: ${this.lastError}`);
        return null;
      }

      const data = await response.json();
      console.log(`📥 Job submitted: ${data.job_id} (queue position: ${data.queue_position})`);
      return data.job_id;
    } catch (error) {
      this.lastError = error instanceof Error ? error.message : String(error);
      console.error(`❌ Queue submit error: ${this.lastError}`);
      return null;
    }
  }

  /**
   * Poll for job status from backend queue
   * Returns the job status object or null if not found
   */
  async getJobStatus(jobId: string): Promise<{
    id: string;
    status: string;
    result: any | null;
    error: string | null;
  } | null> {
    try {
      const backendUrl = systemSettingsService.getBackendUrl();
      const endpoint = `${backendUrl}/api/v1/llm/queue/job/${jobId}`;

      const response = await fetch(endpoint, { headers: getAuthHeaders() });
      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        const errorText = await response.text();
        this.lastError = `Job status error: HTTP ${response.status}: ${errorText}`;
        return null;
      }

      return await response.json();
    } catch (error) {
      this.lastError = error instanceof Error ? error.message : String(error);
      return null;
    }
  }

  /**
   * Get backend queue status (pending/active counts, stats)
   */
  async getQueueStatus(): Promise<{
    pending: number;
    active: number;
    max_concurrent: number;
    rate_limit: number;
    stats: {
      total_submitted: number;
      total_completed: number;
      total_failed: number;
      total_timeout: number;
      parallel_peak: number;
    };
  } | null> {
    try {
      const backendUrl = systemSettingsService.getBackendUrl();
      const endpoint = `${backendUrl}/api/v1/llm/queue/status`;

      const response = await fetch(endpoint, { headers: getAuthHeaders() });
      if (!response.ok) {
        return null;
      }

      return await response.json();
    } catch (error) {
      return null;
    }
  }

  /**
   * Submit to queue and wait for result with polling
   * This is an alternative to the blocking `complete` method that uses the async queue
   * Better for batch processing as it doesn't block the request
   */
  async completeAsync(messages: LLMMessage[], timeout: number = 120000, pollInterval: number = 1000): Promise<LLMResponse | null> {
    const jobId = await this.submitToQueue(messages);
    if (!jobId) {
      return null;
    }

    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const status = await this.getJobStatus(jobId);

      if (!status) {
        console.log(`⏳ Job ${jobId.slice(0, 8)} not found, retrying...`);
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        continue;
      }

      if (status.status === 'completed') {
        console.log(`✅ Job ${jobId.slice(0, 8)} completed`);
        return this.parseResponse(status.result);
      }

      if (status.status === 'failed' || status.status === 'timeout') {
        this.lastError = status.error || `Job ${status.status}`;
        console.error(`❌ Job ${jobId.slice(0, 8)} ${status.status}: ${this.lastError}`);
        return null;
      }

      // Still processing, wait and poll again
      console.log(`⏳ Job ${jobId.slice(0, 8)} status: ${status.status}`);
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    this.lastError = `Job ${jobId} timed out after ${timeout / 1000}s`;
    console.error(`❌ ${this.lastError}`);
    return null;
  }

  /**
   * Submit multiple LLM requests as a batch (async, non-blocking)
   * All requests are processed in parallel on the backend
   *
   * @param requests Array of request objects, each with { messages, priority?, request_id? }
   * @param parallel Use fast parallel mode (default: true)
   * @returns Batch submission result with batch_id and job_ids
   */
  async submitBatch(
    requests: Array<{ messages: LLMMessage[]; priority?: number; request_id?: string }>,
    parallel: boolean = true
  ): Promise<{
    batch_id: string;
    total_requests: number;
    jobs: Array<{ job_id: string; request_id: string; index: number }>;
    status: string;
  } | null> {
    if (!this.config || !this.config.enabled) {
      console.log('❌ LLM submitBatch: Service not enabled');
      return null;
    }

    if (requests.length === 0) {
      console.log('❌ LLM submitBatch: No requests provided');
      return null;
    }

    try {
      const backendUrl = systemSettingsService.getBackendUrl();
      const endpoint = `${backendUrl}/api/v1/llm/batch/submit`;
      console.log(`📦 Submitting batch of ${requests.length} requests to: ${endpoint}`);

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ requests, parallel }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        this.lastError = `Batch submit error: HTTP ${response.status}: ${errorText}`;
        console.error(`❌ Batch submit error: ${this.lastError}`);
        return null;
      }

      const data = await response.json();
      console.log(`📦 Batch submitted: ${data.batch_id} with ${data.total_requests} jobs`);
      return data;
    } catch (error) {
      this.lastError = error instanceof Error ? error.message : String(error);
      console.error(`❌ Batch submit error: ${this.lastError}`);
      return null;
    }
  }

  /**
   * Get status of multiple jobs (batch status)
   */
  async getBatchStatus(jobIds: string[]): Promise<{
    total: number;
    completed: number;
    failed: number;
    pending: number;
    processing: number;
    all_done: boolean;
    success_rate: number;
    jobs: Array<{
      id: string;
      status: string;
      result: any;
      error: string | null;
    }>;
  } | null> {
    if (jobIds.length === 0) {
      return null;
    }

    try {
      const backendUrl = systemSettingsService.getBackendUrl();
      const endpoint = `${backendUrl}/api/v1/llm/batch/status?job_ids=${jobIds.join(',')}`;

      const response = await fetch(endpoint, { headers: getAuthHeaders() });
      if (!response.ok) {
        return null;
      }

      return await response.json();
    } catch (error) {
      return null;
    }
  }

  /**
   * Submit batch and wait for all results
   * Convenience method that combines submit + polling
   *
   * @param requests Array of request objects
   * @param timeout Maximum time to wait in ms (default: 120000)
   * @param pollInterval Time between status checks in ms (default: 1000)
   * @returns Array of parsed LLM responses (in same order as requests)
   */
  async completeBatch(
    requests: Array<{ messages: LLMMessage[]; priority?: number }>,
    timeout: number = 120000,
    pollInterval: number = 1000
  ): Promise<Array<LLMResponse | null>> {
    // Submit batch
    const batchResult = await this.submitBatch(requests);
    if (!batchResult) {
      return requests.map(() => null);
    }

    const jobIds = batchResult.jobs.map(j => j.job_id);
    const startTime = Date.now();

    // Poll for completion
    while (Date.now() - startTime < timeout) {
      const status = await this.getBatchStatus(jobIds);

      if (!status) {
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        continue;
      }

      if (status.all_done) {
        console.log(`✅ Batch ${batchResult.batch_id} complete: ${status.completed}/${status.total} succeeded`);

        // Parse results in order
        const results: Array<LLMResponse | null> = [];
        for (const jobInfo of batchResult.jobs) {
          const jobStatus = status.jobs.find(j => j.id === jobInfo.job_id);
          if (jobStatus && jobStatus.status === 'completed' && jobStatus.result) {
            results.push(this.parseResponse(jobStatus.result));
          } else {
            results.push(null);
          }
        }
        return results;
      }

      console.log(`⏳ Batch ${batchResult.batch_id.slice(0, 12)}: ${status.completed}/${status.total} complete, ${status.processing} processing`);
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    // Timeout - return partial results
    this.lastError = `Batch timeout after ${timeout / 1000}s`;
    console.error(`❌ ${this.lastError}`);

    const finalStatus = await this.getBatchStatus(jobIds);
    if (finalStatus) {
      const results: Array<LLMResponse | null> = [];
      for (const jobInfo of batchResult.jobs) {
        const jobStatus = finalStatus.jobs.find(j => j.id === jobInfo.job_id);
        if (jobStatus && jobStatus.status === 'completed' && jobStatus.result) {
          results.push(this.parseResponse(jobStatus.result));
        } else {
          results.push(null);
        }
      }
      return results;
    }

    return requests.map(() => null);
  }

  /**
   * Parse response based on provider
   */
  private parseResponse(data: any): LLMResponse {
    if (!this.config) {
      return { content: '' };
    }

    switch (this.config.provider) {
      case LLMProvider.OPENAI:
      case LLMProvider.OLLAMA:
      case LLMProvider.CLOUDERA:
      case LLMProvider.CUSTOM:
        return {
          content: data.choices?.[0]?.message?.content || '',
          usage: data.usage
            ? {
                promptTokens: data.usage.prompt_tokens,
                completionTokens: data.usage.completion_tokens,
                totalTokens: data.usage.total_tokens,
              }
            : undefined,
          model: data.model,
        };

      case LLMProvider.ANTHROPIC:
        return {
          content: data.content?.[0]?.text || '',
          usage: data.usage
            ? {
                promptTokens: data.usage.input_tokens,
                completionTokens: data.usage.output_tokens,
                totalTokens: data.usage.input_tokens + data.usage.output_tokens,
              }
            : undefined,
          model: data.model,
        };

      default:
        return {
          content: data.content || data.text || '',
        };
    }
  }

  /**
   * Test connection to LLM endpoint
   */
  async testConnection(): Promise<boolean> {
    try {
      console.log('🧪 Testing LLM connection...');
      const testMessages: LLMMessage[] = [
        {
          role: 'user',
          content: 'Hello, this is a connection test. Please respond with "OK".',
        },
      ];

      console.log('🧪 Sending test request to LLM (45s timeout, priority)...');

      // Use forceRequest=true to skip the enabled check during testing
      // Use 45s timeout for test requests
      // Use priority=true to bypass rate limiting
      const response = await this.complete(testMessages, true, 45000, true);

      const success = response !== null && response.content.length > 0;
      console.log(`🧪 Connection test result: ${success ? 'SUCCESS' : 'FAILED'}`, response);

      if (!success && !this.lastError) {
        this.lastError = 'LLM returned empty response. Check your API key and model configuration.';
      }

      return success;
    } catch (error) {
      console.error('🧪 Connection test failed:', error);
      this.lastError = error instanceof Error ? error.message : String(error);
      return false;
    }
  }

  /**
   * Get current configuration
   */
  /**
   * Load LLM configuration from backend (shared across all users)
   * Falls back to localStorage if backend is unavailable
   */
  async loadConfigFromBackend(): Promise<LLMConfig | null> {
    try {
      console.log('🔌 Loading LLM config from backend...');
      const backendConfig = await getBackendLLMConfig();

      // Convert backend config to frontend LLMConfig format
      const config: LLMConfig = {
        provider: backendConfig.provider as LLMProvider,
        endpoint: backendConfig.endpoint_url || '',
        model: backendConfig.model_name || '',
        writerModel: backendConfig.writer_model_name || undefined,
        writerProvider: (backendConfig.writer_provider as LLMProvider) || undefined,
        writerEndpoint: backendConfig.writer_endpoint_url || undefined,
        writerApiKey: backendConfig.writer_api_key || undefined,
        apiKey: backendConfig.api_key || undefined,
        jwtTokenPath: undefined, // Not stored in backend
        temperature: backendConfig.temperature,
        maxTokens: backendConfig.max_tokens,
        enabled: backendConfig.enabled,
      };

      console.log('✅ Loaded LLM config from backend');

      // Also save to localStorage as backup
      localStorage.setItem('llm_config', JSON.stringify(config));

      return config;
    } catch (error) {
      console.log('⚠️ Backend LLM config not available, checking localStorage...');

      // Fall back to localStorage
      const savedConfig = localStorage.getItem('llm_config');
      if (savedConfig) {
        try {
          const config = JSON.parse(savedConfig);
          console.log('✅ Loaded LLM config from localStorage (backup)');
          return config;
        } catch (err) {
          console.error('Failed to parse localStorage LLM config:', err);
          return null;
        }
      }

      return null;
    }
  }

  /**
   * Save LLM configuration to backend (shared across all users)
   * Also saves to localStorage as backup
   */
  async saveConfigToBackend(config: LLMConfig): Promise<boolean> {
    try {
      console.log('💾 Saving LLM config to backend...');

      // Convert frontend config to backend format.
      // The backend applies this with exclude_unset, so: fields the form owns
      // are sent explicitly (null clears them); jwt_token is OMITTED entirely
      // so saving the form never wipes a JWT stored server-side.
      const backendConfig = {
        provider: config.provider,
        endpoint_url: config.endpoint,
        api_key: config.apiKey ?? null,
        model_name: config.model,
        writer_model_name: config.writerModel || null,
        writer_provider: config.writerProvider || null,
        writer_endpoint_url: config.writerEndpoint || null,
        writer_api_key: config.writerApiKey || null,
        temperature: config.temperature ?? 0.7,
        max_tokens: config.maxTokens ?? 2000,
        enabled: config.enabled ?? false,
      };

      await createOrUpdateLLMConfig(backendConfig);
      console.log('✅ LLM config saved to backend');

      // Also save to localStorage as backup
      localStorage.setItem('llm_config', JSON.stringify(config));
      console.log('✅ LLM config backed up to localStorage');

      return true;
    } catch (error) {
      console.error('❌ Failed to save LLM config to backend:', error);

      // At least save to localStorage
      try {
        localStorage.setItem('llm_config', JSON.stringify(config));
        console.log('⚠️ LLM config saved to localStorage only (backend unavailable)');
        return true;
      } catch (err) {
        console.error('Failed to save to localStorage:', err);
        return false;
      }
    }
  }

  /**
   * Initialize from backend or localStorage
   * Automatically loads config from backend if available
   */
  async initializeFromBackend(): Promise<boolean> {
    const config = await this.loadConfigFromBackend();
    if (config) {
      return await this.initialize(config);
    }
    return false;
  }

  getConfig(): LLMConfig | null {
    return this.config;
  }

  /**
   * Check if service is enabled and configured
   */
  isEnabled(): boolean {
    return this.config?.enabled ?? false;
  }
}

// Singleton instance
export const llmService = new LLMService();
