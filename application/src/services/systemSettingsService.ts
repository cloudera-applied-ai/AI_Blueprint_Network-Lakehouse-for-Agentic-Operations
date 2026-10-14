/**
 * System Settings Service - Manages frontend configuration stored in backend
 * Handles backend URL configuration that's shared across all users
 */

export interface SlackSettings {
  slack_enabled: boolean;
  slack_webhook_url: string | null;
  slack_channel: string;
  slack_notify_alerts: boolean;
  slack_notify_actions: boolean;
  slack_notify_critical_only: boolean;
}

export interface CartoSettings {
  carto_api_key: string | null;
  carto_basemap: string | null;
}

export interface SystemSettings extends Partial<SlackSettings>, Partial<CartoSettings> {
  backend_api_url: string | null;
}

/** Fired on window after basemap settings are saved so the live map can re-tile. */
export const BASEMAP_SETTINGS_CHANGED_EVENT = 'basemap-settings-changed';

export interface SlackStatus {
  enabled: boolean;
  channel: string | null;
  notify_alerts: boolean;
  notify_actions: boolean;
  critical_only: boolean;
  config_source: 'database' | 'environment' | 'none';
  message: string;
}

class SystemSettingsService {
  private static BACKEND_URL_STORAGE_KEY = 'noc_backend_url';
  private settings: SystemSettings | null = null;
  private defaultBackendUrl: string;

  constructor() {
    // Determine the default backend URL:
    // 1. If VITE_API_BASE_URL is set, use it (with HTTPS upgrade if needed)
    // 2. Otherwise use empty string = relative URLs via Vite proxy (works for
    //    both local and external access without needing to know the host)
    const envUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
    const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';

    if (envUrl) {
      if (isHttps && envUrl.startsWith('http://')) {
        this.defaultBackendUrl = envUrl.replace('http://', 'https://');
      } else {
        this.defaultBackendUrl = envUrl;
      }
    } else {
      this.defaultBackendUrl = '';
    }

    // Clear any invalid URLs from localStorage (missing protocol causes CORS errors)
    this.cleanupInvalidStoredUrl();

    console.log('SystemSettingsService initialized, backend URL:', this.getBackendUrl() || '(using proxy)');
  }

  /**
   * Remove invalid or stale backend URLs from localStorage.
   * - URLs without http:// or https:// cause "CORS request not http" browser errors.
   * - localhost URLs are cleared when accessed from a remote machine (prevents
   *   stale dev URLs from breaking Docker/remote deployments).
   */
  private cleanupInvalidStoredUrl(): void {
    try {
      const stored = localStorage.getItem(SystemSettingsService.BACKEND_URL_STORAGE_KEY);
      if (!stored) return;

      // Remove URLs without protocol
      if (!stored.startsWith('http://') && !stored.startsWith('https://')) {
        localStorage.removeItem(SystemSettingsService.BACKEND_URL_STORAGE_KEY);
        console.log('Cleared invalid stored backend URL (missing protocol):', stored);
        return;
      }

      // Remove localhost/127.0.0.1 URLs when page is accessed from a different host
      if (typeof window !== 'undefined') {
        const pageHost = window.location.hostname;
        const isPageLocal = pageHost === 'localhost' || pageHost === '127.0.0.1';
        const isStoredLocal = stored.includes('://localhost') || stored.includes('://127.0.0.1');
        if (!isPageLocal && isStoredLocal) {
          localStorage.removeItem(SystemSettingsService.BACKEND_URL_STORAGE_KEY);
          console.log('Cleared stale localhost backend URL for remote access:', stored);
        }
      }
    } catch {
      // localStorage unavailable
    }
  }

  /**
   * Check if a backend URL has been configured (via env var, localStorage, or settings).
   * An empty string means "use relative URLs via Vite proxy", which is a valid config.
   */
  isBackendConfigured(): boolean {
    // If an explicit URL is set, it's configured
    if (this.getBackendUrl() !== '') return true;
    // Empty string = relative URLs through the Vite proxy, which is valid in dev mode
    return import.meta.env.DEV || this.defaultBackendUrl === '';
  }

  /**
   * Get the current backend API URL.
   * Priority: localStorage (user-entered via BackendSetup) > VITE_API_BASE_URL env var > empty (proxy)
   * Returns empty string to use relative URLs (Vite proxy) when no URL is configured.
   * Note: backend_api_url from server settings is NOT used here — the URL is a
   * client-side concern. In CML combined deployments the browser cannot reach the
   * backend directly; only the Vite proxy (relative URLs) works.
   */
  getBackendUrl(): string {
    let url = '';
    try {
      const localUrl = localStorage.getItem(SystemSettingsService.BACKEND_URL_STORAGE_KEY);
      if (localUrl) {
        url = localUrl;
      }
    } catch {
      // localStorage unavailable
    }
    if (!url) {
      url = this.defaultBackendUrl;
    }
    // Auto-prepend http:// if a host/IP is provided without a protocol.
    // Without a protocol, fetch() treats the value as a relative path segment.
    url = url.trim();
    if (url && !url.startsWith('http://') && !url.startsWith('https://')) {
      url = `http://${url}`;
    }
    // Strip trailing slashes to avoid double-slash in constructed URLs
    return url.replace(/\/+$/, '');
  }

  /**
   * Save backend URL to localStorage so it persists even when the backend is down.
   * This allows users to configure the URL from the error screen.
   */
  saveBackendUrlLocally(url: string): void {
    try {
      if (url) {
        // Ensure URL has a protocol to avoid CORS errors
        let validUrl = url.trim();
        if (validUrl && !validUrl.startsWith('http://') && !validUrl.startsWith('https://')) {
          validUrl = `http://${validUrl}`;
        }
        localStorage.setItem(SystemSettingsService.BACKEND_URL_STORAGE_KEY, validUrl);
      } else {
        localStorage.removeItem(SystemSettingsService.BACKEND_URL_STORAGE_KEY);
      }
    } catch {
      // localStorage unavailable
    }
  }

  /**
   * Load system settings from backend
   */
  async loadSettings(): Promise<SystemSettings | null> {
    try {
      console.log('🔧 Loading system settings from backend...');

      // Use resolved URL (includes CML auto-detection and localStorage override)
      const apiKey = import.meta.env.VITE_API_KEY || 'dev-api-key-change-me';
      const response = await fetch(`${this.getBackendUrl()}/api/v1/system/settings`, {
        headers: {
          'X-API-Key': apiKey,
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          console.log('⚠️ No system settings found in backend (using defaults)');
          return null;
        }
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      this.settings = await response.json();

      console.log('✅ Loaded system settings from backend');
      return this.settings;
    } catch (error) {
      console.log('⚠️ Could not load system settings, using defaults:', error);
      return null;
    }
  }

  /**
   * Save system settings to backend
   */
  async saveSettings(settings: SystemSettings): Promise<boolean> {
    try {
      console.log('💾 Saving system settings to backend...');

      // Normalize backend_api_url before saving: ensure it has a protocol
      if (settings.backend_api_url) {
        let normalized = settings.backend_api_url.trim();
        if (normalized && !normalized.startsWith('http://') && !normalized.startsWith('https://')) {
          normalized = `http://${normalized}`;
        }
        settings = { ...settings, backend_api_url: normalized };
      }

      const apiKey = import.meta.env.VITE_API_KEY || 'dev-api-key-change-me';
      const response = await fetch(`${this.getBackendUrl()}/api/v1/system/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify(settings),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      this.settings = await response.json();
      console.log('✅ System settings saved to backend');
      return true;
    } catch (error) {
      console.error('❌ Failed to save system settings:', error);
      return false;
    }
  }

  /**
   * Get current settings
   */
  getSettings(): SystemSettings | null {
    return this.settings;
  }

  /**
   * Get default backend URL (from .env)
   */
  getDefaultBackendUrl(): string {
    return this.defaultBackendUrl;
  }

  /**
   * Get Slack integration status
   */
  async getSlackStatus(): Promise<SlackStatus | null> {
    try {
      const response = await fetch(`${this.getBackendUrl()}/api/v1/slack/status`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Failed to get Slack status:', error);
      return null;
    }
  }

  /**
   * Test Slack connection by sending a test message
   */
  async testSlackConnection(): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${this.getBackendUrl()}/api/v1/slack/test`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        return {
          success: false,
          message: errorData.detail || `HTTP ${response.status}`,
        };
      }

      const data = await response.json();
      return {
        success: true,
        message: data.message || 'Test notification sent successfully!',
      };
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Connection failed',
      };
    }
  }
}

// Singleton instance
export const systemSettingsService = new SystemSettingsService();
