import { memo, useState, useEffect } from 'react';
import { LLMConfig, LLMProvider } from '@/types/llm';
import { llmService } from '@/services/llmService';
import { testBackendLLMConnection } from '@/services/api/llmApi';
import { systemSettingsService, SlackSettings, CartoSettings, BASEMAP_SETTINGS_CHANGED_EVENT } from '@/services/systemSettingsService';
import { CARTO_BASEMAP_STYLES, ENV_CARTO_API_KEY, ENV_CARTO_BASEMAP } from '@/config/basemap';
import { Settings, Check, X, AlertCircle, Info, RefreshCw, Database, Globe, Cloud, MessageSquare, Zap, Trash2, Map } from 'lucide-react';
import ClouderaServicesPanel from './ClouderaServicesPanel';

interface AISettingsPanelProps {
  onClose: () => void;
  onRegenerateData?: () => void;
}

const AISettingsPanel = memo(({ onClose, onRegenerateData }: AISettingsPanelProps) => {
  const [config, setConfig] = useState<LLMConfig>({
    enabled: false,
    provider: LLMProvider.OPENAI,
    endpoint: 'https://api.openai.com/v1/chat/completions',
    model: '',
    apiKey: '',
    jwtTokenPath: '/tmp/jwt',
    temperature: 0.7,
    maxTokens: 2000,
  });

  const [backendUrl, setBackendUrl] = useState<string>('');
  const [backendUrlSaved, setBackendUrlSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);
  const [testMessage, setTestMessage] = useState('');
  const [testingWriter, setTestingWriter] = useState(false);
  const [writerTestResult, setWriterTestResult] = useState<'success' | 'error' | null>(null);
  const [writerTestMessage, setWriterTestMessage] = useState('');
  const [saved, setSaved] = useState(false);
  const [showClouderaServices, setShowClouderaServices] = useState(false);

  // Slack configuration state
  const [slackConfig, setSlackConfig] = useState<SlackSettings>({
    slack_enabled: false,
    slack_webhook_url: null,
    slack_channel: '#network-alerts',
    slack_notify_alerts: true,
    slack_notify_actions: true,
    slack_notify_critical_only: false,
  });
  const [slackSaved, setSlackSaved] = useState(false);

  // CARTO basemap state
  const [cartoConfig, setCartoConfig] = useState<CartoSettings>({
    carto_api_key: null,
    carto_basemap: null,
  });
  const [cartoSaved, setCartoSaved] = useState(false);
  const [cartoError, setCartoError] = useState<string | null>(null);
  const [slackTesting, setSlackTesting] = useState(false);
  const [slackTestResult, setSlackTestResult] = useState<'success' | 'error' | null>(null);
  const [slackTestMessage, setSlackTestMessage] = useState('');

  // AI Optimization settings state
  const [aiOptimization, setAiOptimization] = useState({
    llm_sample_rate: 5,
    node_cooldown_minutes: 15,
    cache_ttl_minutes: 30,
    cache_size: 0,
    nodes_on_cooldown: 0,
  });
  const [aiOptimizationStats, setAiOptimizationStats] = useState({
    ai_analyses_llm: 0,
    ai_analyses_rule_based: 0,
    ai_analyses_cached: 0,
    ai_analyses_cooled_down: 0,
  });
  const [aiOptSaving, setAiOptSaving] = useState(false);
  const [aiOptSaved, setAiOptSaved] = useState(false);
  const [aiOptClearing, setAiOptClearing] = useState(false);

  // Load saved config and backend URL on mount
  useEffect(() => {
    const savedConfig = localStorage.getItem('llm_config');
    if (savedConfig) {
      try {
        const parsed = JSON.parse(savedConfig);
        // Merge with defaults to ensure all fields are defined (prevents controlled/uncontrolled warning)
        setConfig(prev => ({
          ...prev,
          ...parsed,
          // Ensure string fields are never undefined
          endpoint: parsed.endpoint || prev.endpoint || '',
          model: parsed.model || prev.model || '',
          writerModel: parsed.writerModel || '',
          writerProvider: parsed.writerProvider || '',
          writerEndpoint: parsed.writerEndpoint || '',
          writerApiKey: parsed.writerApiKey || '',
          apiKey: parsed.apiKey || '',
          jwtTokenPath: parsed.jwtTokenPath || '',
          temperature: parsed.temperature ?? prev.temperature ?? 0.7,
          maxTokens: parsed.maxTokens ?? prev.maxTokens ?? 2000,
        }));
      } catch (error) {
        console.error('Error loading saved config:', error);
      }
    }

    // Load backend URL and Slack settings from system settings
    const settings = systemSettingsService.getSettings();
    if (settings?.backend_api_url) {
      setBackendUrl(settings.backend_api_url);
    } else {
      // Use default URL from .env
      setBackendUrl(systemSettingsService.getDefaultBackendUrl());
    }

    // Load Slack settings
    if (settings) {
      setSlackConfig(prev => ({
        ...prev,
        slack_enabled: settings.slack_enabled ?? false,
        slack_webhook_url: settings.slack_webhook_url ?? null,
        slack_channel: settings.slack_channel ?? '#network-alerts',
        slack_notify_alerts: settings.slack_notify_alerts ?? true,
        slack_notify_actions: settings.slack_notify_actions ?? true,
        slack_notify_critical_only: settings.slack_notify_critical_only ?? false,
      }));
      setCartoConfig({
        carto_api_key: settings.carto_api_key ?? null,
        carto_basemap: settings.carto_basemap ?? null,
      });
    }

    // Load AI Optimization settings
    fetchAiOptimizationSettings();
  }, []);

  const fetchAiOptimizationSettings = async () => {
    try {
      const backendUrl = systemSettingsService.getBackendUrl();
      const response = await fetch(`${backendUrl}/api/v1/ai-optimization`);
      if (response.ok) {
        const data = await response.json();
        setAiOptimization(data.settings);
        setAiOptimizationStats(data.stats);
      }
    } catch (error) {
      console.error('Failed to fetch AI optimization settings:', error);
    }
  };

  // Update the endpoint preset when the provider changes. The model name is
  // never pre-filled or overwritten: it is whatever the user configured.
  const handleProviderChange = (provider: LLMProvider) => {
    let endpoint = config.endpoint;

    switch (provider) {
      case LLMProvider.OPENAI:
        endpoint = 'https://api.openai.com/v1/chat/completions';
        break;
      case LLMProvider.ANTHROPIC:
        endpoint = 'https://api.anthropic.com/v1/messages';
        break;
      case LLMProvider.OLLAMA:
        endpoint = 'http://localhost:11434';
        break;
      case LLMProvider.CLOUDERA:
      case LLMProvider.CUSTOM:
        // User enters the endpoint from their own deployment
        endpoint = '';
        break;
    }

    setConfig({ ...config, provider, endpoint });
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    setTestMessage('');

    try {
      // First save config to backend with enabled=true for testing
      setTestMessage('Saving configuration to backend...');
      const testConfig = { ...config, enabled: true };
      const configSaved = await llmService.saveConfigToBackend(testConfig);
      if (!configSaved) {
        setTestResult('error');
        setTestMessage('Failed to save configuration to backend. Check backend connection.');
        setTesting(false);
        return;
      }

      // Initialize with enabled=true for testing purposes
      setTestMessage('Initializing LLM service...');
      const success = await llmService.initialize(testConfig);

      if (!success) {
        setTestResult('error');
        const errorMsg = llmService.lastError || 'Failed to initialize LLM service. Check your configuration.';
        setTestMessage(errorMsg);
        setTesting(false);
        return;
      }

      // Test the connection
      setTestMessage('Testing LLM connection (this may take up to 45 seconds)...');
      console.log('🧪 AISettingsPanel: Starting test connection...');
      const connected = await llmService.testConnection();
      console.log('🧪 AISettingsPanel: Test connection result:', connected);

      if (connected) {
        console.log('🧪 AISettingsPanel: Setting success state');
        setTestResult('success');
        setTestMessage('Connection successful! LLM service is ready.');
        // Update the local config to enabled since test passed
        setConfig(prev => ({ ...prev, enabled: true }));
      } else {
        console.log('🧪 AISettingsPanel: Setting error state');
        setTestResult('error');
        const errorMsg = llmService.lastError || 'Connection failed. Please check your endpoint, API key, or JWT token.';
        setTestMessage(errorMsg);
      }
    } catch (error) {
      console.error('🧪 AISettingsPanel: Test error:', error);
      setTestResult('error');
      setTestMessage(error instanceof Error ? error.message : 'An unexpected error occurred');
    } finally {
      console.log('🧪 AISettingsPanel: Setting testing to false');
      setTesting(false);
    }
  };

  const handleTestWriter = async () => {
    setTestingWriter(true);
    setWriterTestResult(null);
    setWriterTestMessage('');

    try {
      // Save first so the backend probes exactly what's on screen.
      setWriterTestMessage('Saving configuration to backend...');
      const testConfig = { ...config, enabled: true };
      const configSaved = await llmService.saveConfigToBackend(testConfig);
      if (!configSaved) {
        setWriterTestResult('error');
        setWriterTestMessage('Failed to save configuration to backend. Check backend connection.');
        return;
      }

      setWriterTestMessage('Testing writer model (this may take up to a minute)...');
      const result = await testBackendLLMConnection('writer');
      setWriterTestResult(result.ok ? 'success' : 'error');
      setWriterTestMessage(
        result.ok ? `Writer model responded: ${result.message}` : result.message
      );
    } catch (error) {
      setWriterTestResult('error');
      setWriterTestMessage(error instanceof Error ? error.message : 'An unexpected error occurred');
    } finally {
      setTestingWriter(false);
    }
  };

  const handleSave = async () => {
    // Save config to backend (also saves to localStorage as backup)
    const saved = await llmService.saveConfigToBackend(config);

    if (saved) {
      // Initialize LLM service with the saved config
      await llmService.initialize(config);

      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } else {
      console.error('Failed to save LLM configuration');
      // Still try to initialize even if save failed
      await llmService.initialize(config);
    }
  };

  const handleSaveBackendUrl = async () => {
    // Always save to localStorage so the URL persists even if the backend is unreachable
    systemSettingsService.saveBackendUrlLocally(backendUrl || '');

    // Try to save to backend database too
    const success = await systemSettingsService.saveSettings({
      backend_api_url: backendUrl || null,
    });

    if (success) {
      setBackendUrlSaved(true);
      setTimeout(() => setBackendUrlSaved(false), 2000);
    } else {
      // Backend unreachable — localStorage save is enough, reload to use new URL
      setBackendUrlSaved(true);
      setTimeout(() => window.location.reload(), 500);
    }
  };

  const handleSaveSlackConfig = async () => {
    const success = await systemSettingsService.saveSettings({
      backend_api_url: backendUrl || null,
      ...slackConfig,
      ...cartoConfig,
    });

    if (success) {
      setSlackSaved(true);
      setTimeout(() => setSlackSaved(false), 2000);
    } else {
      console.error('Failed to save Slack configuration');
    }
  };

  const handleSaveCartoConfig = async () => {
    setCartoError(null);
    const success = await systemSettingsService.saveSettings({
      backend_api_url: backendUrl || null,
      ...slackConfig,
      carto_api_key: cartoConfig.carto_api_key?.trim() || null,
      carto_basemap: cartoConfig.carto_basemap || null,
    });

    if (success) {
      setCartoSaved(true);
      setTimeout(() => setCartoSaved(false), 2000);
      // Tell the live map to swap its tile URL without a page reload
      window.dispatchEvent(new CustomEvent(BASEMAP_SETTINGS_CHANGED_EVENT));
    } else {
      setCartoError('Failed to save basemap settings — check the backend connection.');
    }
  };

  const handleTestSlack = async () => {
    setSlackTesting(true);
    setSlackTestResult(null);
    setSlackTestMessage('');

    // First save the current config
    const saved = await systemSettingsService.saveSettings({
      backend_api_url: backendUrl || null,
      ...slackConfig,
    });

    if (!saved) {
      setSlackTestResult('error');
      setSlackTestMessage('Failed to save Slack configuration before testing');
      setSlackTesting(false);
      return;
    }

    // Then test the connection
    const result = await systemSettingsService.testSlackConnection();
    setSlackTestResult(result.success ? 'success' : 'error');
    setSlackTestMessage(result.message);
    setSlackTesting(false);
  };

  const handleSaveAiOptimization = async () => {
    setAiOptSaving(true);
    try {
      const backendUrl = systemSettingsService.getBackendUrl();
      const params = new URLSearchParams({
        llm_sample_rate: aiOptimization.llm_sample_rate.toString(),
        node_cooldown_minutes: aiOptimization.node_cooldown_minutes.toString(),
        cache_ttl_minutes: aiOptimization.cache_ttl_minutes.toString(),
      });
      const response = await fetch(`${backendUrl}/api/v1/ai-optimization?${params}`, {
        method: 'PUT',
      });
      if (response.ok) {
        setAiOptSaved(true);
        setTimeout(() => setAiOptSaved(false), 2000);
        // Refresh stats
        await fetchAiOptimizationSettings();
      }
    } catch (error) {
      console.error('Failed to save AI optimization settings:', error);
    } finally {
      setAiOptSaving(false);
    }
  };

  const handleClearAiCache = async () => {
    setAiOptClearing(true);
    try {
      const backendUrl = systemSettingsService.getBackendUrl();
      const response = await fetch(`${backendUrl}/api/v1/ai-optimization/clear-cache`, {
        method: 'POST',
      });
      if (response.ok) {
        // Refresh stats
        await fetchAiOptimizationSettings();
      }
    } catch (error) {
      console.error('Failed to clear AI cache:', error);
    } finally {
      setAiOptClearing(false);
    }
  };

  const getProviderInfo = (provider: LLMProvider): string => {
    switch (provider) {
      case LLMProvider.OPENAI:
        return 'OpenAI GPT models (GPT-4, GPT-3.5)';
      case LLMProvider.ANTHROPIC:
        return 'Anthropic AI models';
      case LLMProvider.OLLAMA:
        return 'Ollama local inference (Llama 3, Mistral, Gemma, etc.)';
      case LLMProvider.CLOUDERA:
        return 'Cloudera ML - Nemotron 4.9B (OpenAI-compatible endpoint)';
      case LLMProvider.CUSTOM:
        return 'Custom OpenAI-compatible endpoint';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[1100]">
      <div className="bg-gray-800 rounded-lg shadow-xl border border-gray-700 p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Settings className="w-6 h-6 text-blue-500" />
            <div>
              <h2 className="text-xl font-bold text-white">AI Agent Settings</h2>
              <p className="text-sm text-gray-400">Configure LLM for intelligent network analysis</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Enable/Disable Toggle */}
        <div className="mb-6 p-4 bg-gray-750 rounded-lg border border-gray-700">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={config.enabled}
              onChange={(e) => setConfig({ ...config, enabled: e.target.checked })}
              className="w-5 h-5 rounded text-blue-600 focus:ring-2 focus:ring-blue-500"
            />
            <div>
              <span className="text-white font-medium">Enable AI Agents</span>
              <p className="text-sm text-gray-400">Use LLM for enhanced analysis and recommendations</p>
            </div>
          </label>
        </div>

        {/* Provider Selection */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            LLM Provider
          </label>
          <select
            value={config.provider}
            onChange={(e) => handleProviderChange(e.target.value as LLMProvider)}
            className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          >
            <option value={LLMProvider.OPENAI}>OpenAI</option>
            <option value={LLMProvider.ANTHROPIC}>Anthropic</option>
            <option value={LLMProvider.OLLAMA}>Ollama (Local)</option>
            <option value={LLMProvider.CLOUDERA}>Cloudera ML</option>
            <option value={LLMProvider.CUSTOM}>Custom Endpoint</option>
          </select>
          <p className="text-xs text-gray-400 mt-1">{getProviderInfo(config.provider)}</p>
        </div>

        {/* Endpoint URL */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Endpoint URL
          </label>
          <input
            type="text"
            value={config.endpoint}
            onChange={(e) => setConfig({ ...config, endpoint: e.target.value })}
            placeholder={
              config.provider === LLMProvider.CLOUDERA
                ? 'https://ml-xxxxx.cloudera.site/namespaces/.../endpoints/.../v1'
                : 'https://api.example.com/v1/chat/completions'
            }
            className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-mono text-sm"
          />
          {config.provider === LLMProvider.CLOUDERA && (
            <p className="text-xs text-blue-400 mt-1">
              💡 Enter base endpoint ending in /v1 (we'll add /chat/completions automatically)
            </p>
          )}
        </div>

        {/* Model Name */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Model Name
          </label>
          <input
            type="text"
            value={config.model}
            onChange={(e) => setConfig({ ...config, model: e.target.value })}
            placeholder={
              config.provider === LLMProvider.CLOUDERA
                ? 'nvidia/llama-3.3-nemotron-super-49b-v1'
                : config.provider === LLMProvider.OPENAI
                ? 'gpt-4'
                : config.provider === LLMProvider.ANTHROPIC
                ? 'anthropic-model'
                : 'model-name'
            }
            className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-mono text-sm"
          />
          {config.provider === LLMProvider.CLOUDERA ? (
            <p className="text-xs text-blue-400 mt-1">
              💡 Copy the exact model name from your Cloudera ML deployment curl command
            </p>
          ) : (
            <p className="text-xs text-gray-400 mt-1">
              Examples: gpt-4, anthropic-model, foundation-sec:8b (security analyst model)
            </p>
          )}
        </div>

        {/* Writer Model (optional) — two-model mode */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Writer Model <span className="text-gray-500 font-normal">(optional)</span>
          </label>
          <input
            type="text"
            value={config.writerModel || ''}
            onChange={(e) => setConfig({ ...config, writerModel: e.target.value })}
            placeholder="e.g. qwen2.5 (leave blank to use the model above for everything)"
            className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-mono text-sm"
          />
          <p className="text-xs text-gray-400 mt-1">
            When set, a generalist model (e.g. Qwen) writes the analysis prose, reports, and chat,
            while the Model Name above (e.g. Cisco Foundation-Sec-8B) handles security detection and
            structured findings.
          </p>

          {config.writerModel ? (
            <div className="mt-3 pl-3 border-l-2 border-gray-700 space-y-3">
              <p className="text-xs text-gray-500">
                Optional — put the writer on a <span className="text-gray-300">different endpoint</span>.
                Leave the endpoint blank to share the analyst endpoint and credentials above
                (provider/key below only apply when an endpoint is set). Note: a Cloudera AI
                Inference endpoint serves a single model — a second model name on the analyst
                endpoint only works on multi-model servers like Ollama.
              </p>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Writer Provider</label>
                <select
                  value={config.writerProvider || ''}
                  onChange={(e) => setConfig({ ...config, writerProvider: e.target.value as LLMProvider | '' })}
                  className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-blue-500 text-sm"
                >
                  <option value="">Same as analyst</option>
                  <option value={LLMProvider.OLLAMA}>Ollama</option>
                  <option value={LLMProvider.CLOUDERA}>Cloudera</option>
                  <option value={LLMProvider.OPENAI}>OpenAI</option>
                  <option value={LLMProvider.ANTHROPIC}>Anthropic</option>
                  <option value={LLMProvider.CUSTOM}>Custom</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Writer Endpoint URL</label>
                <input
                  type="text"
                  value={config.writerEndpoint || ''}
                  onChange={(e) => setConfig({ ...config, writerEndpoint: e.target.value })}
                  placeholder="e.g. http://qwen-host:11434/v1 (blank = analyst endpoint)"
                  className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-blue-500 font-mono text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Writer API Key / Token</label>
                <input
                  type="password"
                  value={config.writerApiKey || ''}
                  onChange={(e) => setConfig({ ...config, writerApiKey: e.target.value })}
                  placeholder="blank = analyst JWT (Cloudera) or no auth (Ollama)"
                  className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-blue-500 font-mono text-sm"
                />
              </div>
              <div>
                <button
                  onClick={handleTestWriter}
                  disabled={testingWriter}
                  className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white text-sm rounded-md border border-gray-600"
                >
                  {testingWriter ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Zap className="w-3.5 h-3.5" />
                  )}
                  Test Writer Model
                </button>
                {(writerTestMessage || writerTestResult) && (
                  <p
                    className={`text-xs mt-2 ${
                      writerTestResult === 'success'
                        ? 'text-green-400'
                        : writerTestResult === 'error'
                          ? 'text-red-400'
                          : 'text-gray-400'
                    }`}
                  >
                    {writerTestResult === 'success' ? '✓ ' : writerTestResult === 'error' ? '✗ ' : ''}
                    {writerTestMessage}
                  </p>
                )}
              </div>
            </div>
          ) : null}
        </div>

        {/* Authentication Section */}
        <div className="mb-6 p-4 bg-gray-750 rounded-lg border border-gray-700">
          <div className="flex items-center gap-2 mb-3">
            <AlertCircle className="w-4 h-4 text-yellow-500" />
            <h3 className="text-sm font-semibold text-white">Authentication</h3>
          </div>

          {/* JWT Token Path */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              JWT Token File Path (Optional)
            </label>
            <input
              type="text"
              value={config.jwtTokenPath}
              onChange={(e) => setConfig({ ...config, jwtTokenPath: e.target.value })}
              placeholder="/tmp/jwt"
              className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-400 mt-1">
              If JWT token file exists, it will be used for authentication (refreshed every 30 min)
            </p>
          </div>

          {/* API Key */}
          <div className="mb-2">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {config.provider === LLMProvider.CLOUDERA ? 'CDP Token' : 'API Key'}
            </label>
            <input
              type="password"
              value={config.apiKey}
              onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
              placeholder={
                config.provider === LLMProvider.CLOUDERA
                  ? 'Your Cloudera CDP_TOKEN'
                  : 'sk-...'
              }
              className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-mono text-sm"
            />
            {config.provider === LLMProvider.CLOUDERA ? (
              <p className="text-xs text-blue-400 mt-1">
                💡 Get your CDP token from: Cloudera ML → User Settings → API Keys
              </p>
            ) : (
              <p className="text-xs text-gray-400 mt-1">
                Used if JWT token is not available
              </p>
            )}
          </div>
        </div>

        {/* Advanced Settings */}
        <div className="mb-6">
          <button
            onClick={() => setConfig({ ...config })}
            className="text-sm text-blue-400 hover:text-blue-300 mb-3"
          >
            Advanced Settings
          </button>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Temperature
              </label>
              <input
                type="number"
                min="0"
                max="2"
                step="0.1"
                value={config.temperature}
                onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
                className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-400 mt-1">0.0 = deterministic, 1.0 = creative</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Max Tokens
              </label>
              <input
                type="number"
                min="100"
                max="4000"
                step="100"
                value={config.maxTokens}
                onChange={(e) => setConfig({ ...config, maxTokens: parseInt(e.target.value) })}
                className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-400 mt-1">Response length limit</p>
            </div>
          </div>
        </div>

        {/* AI Cost Optimization Section */}
        <div className="mb-6 p-4 bg-gray-750 rounded-lg border border-gray-700">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-5 h-5 text-yellow-500" />
            <h3 className="text-sm font-semibold text-white">AI Cost Optimization</h3>
          </div>
          <p className="text-sm text-gray-400 mb-4">
            Reduce AI API costs by using rule-based analysis for most alerts. LLM is only used for a sample of alerts.
          </p>

          {/* LLM Usage Stats */}
          <div className="mb-4 p-3 bg-gray-800 rounded-lg">
            <div className="grid grid-cols-4 gap-2 text-center">
              <div>
                <div className="text-lg font-bold text-blue-400">{aiOptimizationStats.ai_analyses_llm}</div>
                <div className="text-xs text-gray-400">LLM Calls</div>
              </div>
              <div>
                <div className="text-lg font-bold text-green-400">{aiOptimizationStats.ai_analyses_rule_based}</div>
                <div className="text-xs text-gray-400">Rule-Based</div>
              </div>
              <div>
                <div className="text-lg font-bold text-purple-400">{aiOptimizationStats.ai_analyses_cached}</div>
                <div className="text-xs text-gray-400">Cached</div>
              </div>
              <div>
                <div className="text-lg font-bold text-orange-400">{aiOptimizationStats.ai_analyses_cooled_down}</div>
                <div className="text-xs text-gray-400">Skipped</div>
              </div>
            </div>
          </div>

          {/* LLM Sample Rate */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              LLM Sample Rate: <span className="text-yellow-400">1 in {aiOptimization.llm_sample_rate}</span> alerts
              <span className="text-gray-500 ml-2">({Math.round(100 / aiOptimization.llm_sample_rate)}% use LLM)</span>
            </label>
            <input
              type="range"
              min="1"
              max="20"
              value={aiOptimization.llm_sample_rate}
              onChange={(e) => setAiOptimization({ ...aiOptimization, llm_sample_rate: parseInt(e.target.value) })}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-yellow-500"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>All LLM (expensive)</span>
              <span>Mostly rules (cheap)</span>
            </div>
          </div>

          {/* Node Cooldown */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Node Cooldown: <span className="text-yellow-400">{aiOptimization.node_cooldown_minutes} minutes</span>
              <span className="text-gray-500 ml-2">({aiOptimization.nodes_on_cooldown} nodes cooling)</span>
            </label>
            <input
              type="range"
              min="0"
              max="60"
              step="5"
              value={aiOptimization.node_cooldown_minutes}
              onChange={(e) => setAiOptimization({ ...aiOptimization, node_cooldown_minutes: parseInt(e.target.value) })}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-yellow-500"
            />
            <p className="text-xs text-gray-400 mt-1">
              Skip re-analyzing same node within this period. Set to 0 to disable.
            </p>
          </div>

          {/* Cache TTL */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Cache Duration: <span className="text-yellow-400">{aiOptimization.cache_ttl_minutes} minutes</span>
              <span className="text-gray-500 ml-2">({aiOptimization.cache_size} cached)</span>
            </label>
            <input
              type="range"
              min="0"
              max="120"
              step="5"
              value={aiOptimization.cache_ttl_minutes}
              onChange={(e) => setAiOptimization({ ...aiOptimization, cache_ttl_minutes: parseInt(e.target.value) })}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-yellow-500"
            />
            <p className="text-xs text-gray-400 mt-1">
              Reuse analysis for similar alerts (same type + severity + region). Set to 0 to disable.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={handleClearAiCache}
              disabled={aiOptClearing}
              className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              {aiOptClearing ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                <Trash2 className="w-4 h-4" />
              )}
              Clear Cache
            </button>
            <button
              onClick={handleSaveAiOptimization}
              disabled={aiOptSaving}
              className="flex-1 px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            >
              {aiOptSaved ? (
                <>
                  <Check className="w-4 h-4" />
                  Saved!
                </>
              ) : aiOptSaving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Saving...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Save Optimization Settings
                </>
              )}
            </button>
          </div>
        </div>

        {/* Test Connection */}
        {testResult && (
          <div
            className={`mb-4 p-3 rounded-lg flex items-start gap-3 ${
              testResult === 'success'
                ? 'bg-green-900/30 border border-green-700'
                : 'bg-red-900/30 border border-red-700'
            }`}
          >
            {testResult === 'success' ? (
              <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
            ) : (
              <X className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            )}
            <div>
              <p className={`text-sm font-medium ${testResult === 'success' ? 'text-green-400' : 'text-red-400'}`}>
                {testResult === 'success' ? 'Connection Successful' : 'Connection Failed'}
              </p>
              <p className="text-sm text-gray-300 mt-1">{testMessage}</p>
            </div>
          </div>
        )}

        {/* Info Box */}
        <div className="mb-6 p-3 bg-blue-900/20 border border-blue-700 rounded-lg flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-gray-300">
            <p className="font-medium text-blue-400 mb-1">How it works:</p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>AI agents analyze alerts and provide root cause analysis</li>
              <li>Pattern detection across multiple nodes and regions</li>
              <li>Enhanced self-healing with AI-powered reasoning</li>
              <li>Predictive analytics for proactive maintenance</li>
            </ul>
          </div>
        </div>

        {/* Data Management Section */}
        {onRegenerateData && (
          <div className="mb-6 p-4 bg-gray-750 rounded-lg border border-gray-700">
            <div className="flex items-center gap-2 mb-3">
              <Database className="w-5 h-5 text-orange-500" />
              <h3 className="text-sm font-semibold text-white">Data Management</h3>
            </div>
            <p className="text-sm text-gray-400 mb-4">
              Regenerate all network data including nodes, 60 days of historical KPIs, alerts, actions, and sensor data.
            </p>
            <button
              onClick={() => {
                onClose();
                onRegenerateData();
              }}
              className="w-full px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 transition-colors flex items-center justify-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Regenerate All Data (60 Days)
            </button>
            <p className="text-xs text-orange-400 mt-2">
              ⚠️ Warning: This will delete all existing data and may take up to a minute to complete.
            </p>
          </div>
        )}

        {/* Backend Configuration Section */}
        <div className="mb-6 p-4 bg-gray-750 rounded-lg border border-gray-700">
          <div className="flex items-center gap-2 mb-3">
            <Globe className="w-5 h-5 text-blue-500" />
            <h3 className="text-sm font-semibold text-white">Backend Configuration</h3>
          </div>
          <p className="text-sm text-gray-400 mb-4">
            Configure the backend API URL. This setting is saved in the backend database and shared across all users.
          </p>

          <div className="mb-3">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Backend API URL
            </label>
            <input
              type="text"
              value={backendUrl}
              onChange={(e) => setBackendUrl(e.target.value)}
              placeholder="https://celltowergenerator.previewhub.dev"
              className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-mono text-sm mb-2"
            />
            <p className="text-xs text-gray-400">
              Default (from .env): <span className="text-blue-400 font-mono">{systemSettingsService.getDefaultBackendUrl()}</span>
            </p>
          </div>

          <button
            onClick={handleSaveBackendUrl}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
          >
            {backendUrlSaved ? (
              <>
                <Check className="w-4 h-4" />
                Saved!
              </>
            ) : (
              <>
                <Globe className="w-4 h-4" />
                Save Backend URL
              </>
            )}
          </button>

          <p className="text-xs text-blue-400 mt-2">
            💡 After saving, refresh the page to connect to the new backend URL.
          </p>
        </div>

        {/* Slack Integration Section */}
        <div className="mb-6 p-4 bg-gray-750 rounded-lg border border-gray-700">
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare className="w-5 h-5 text-purple-500" />
            <h3 className="text-sm font-semibold text-white">Slack Integration</h3>
          </div>
          <p className="text-sm text-gray-400 mb-4">
            Configure Slack notifications for network alerts and self-healing actions.
          </p>

          {/* Enable Toggle */}
          <label className="flex items-center gap-3 cursor-pointer mb-4">
            <input
              type="checkbox"
              checked={slackConfig.slack_enabled}
              onChange={(e) => setSlackConfig({ ...slackConfig, slack_enabled: e.target.checked })}
              className="w-5 h-5 rounded text-purple-600 focus:ring-2 focus:ring-purple-500"
            />
            <div>
              <span className="text-white font-medium">Enable Slack Notifications</span>
              <p className="text-xs text-gray-400">Send alerts and actions to Slack</p>
            </div>
          </label>

          {/* Webhook URL */}
          <div className="mb-3">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Webhook URL
            </label>
            <input
              type="password"
              value={slackConfig.slack_webhook_url || ''}
              onChange={(e) => setSlackConfig({ ...slackConfig, slack_webhook_url: e.target.value || null })}
              placeholder="https://hooks.slack.com/services/T.../B.../..."
              className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 font-mono text-sm"
            />
            <p className="text-xs text-gray-400 mt-1">
              Create an incoming webhook in your Slack workspace settings
            </p>
          </div>

          {/* Channel */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Channel
            </label>
            <input
              type="text"
              value={slackConfig.slack_channel}
              onChange={(e) => setSlackConfig({ ...slackConfig, slack_channel: e.target.value })}
              placeholder="#network-alerts"
              className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 font-mono text-sm"
            />
          </div>

          {/* Notification Options */}
          <div className="mb-4 space-y-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={slackConfig.slack_notify_alerts}
                onChange={(e) => setSlackConfig({ ...slackConfig, slack_notify_alerts: e.target.checked })}
                className="w-4 h-4 rounded text-purple-600 focus:ring-2 focus:ring-purple-500"
              />
              <span className="text-sm text-gray-300">Notify on new alerts</span>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={slackConfig.slack_notify_actions}
                onChange={(e) => setSlackConfig({ ...slackConfig, slack_notify_actions: e.target.checked })}
                className="w-4 h-4 rounded text-purple-600 focus:ring-2 focus:ring-purple-500"
              />
              <span className="text-sm text-gray-300">Notify on self-healing actions</span>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={slackConfig.slack_notify_critical_only}
                onChange={(e) => setSlackConfig({ ...slackConfig, slack_notify_critical_only: e.target.checked })}
                className="w-4 h-4 rounded text-purple-600 focus:ring-2 focus:ring-purple-500"
              />
              <span className="text-sm text-gray-300">Critical alerts only</span>
            </label>
          </div>

          {/* Test Result */}
          {slackTestResult && (
            <div
              className={`mb-4 p-3 rounded-lg flex items-start gap-3 ${
                slackTestResult === 'success'
                  ? 'bg-green-900/30 border border-green-700'
                  : 'bg-red-900/30 border border-red-700'
              }`}
            >
              {slackTestResult === 'success' ? (
                <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
              ) : (
                <X className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              )}
              <div>
                <p className={`text-sm font-medium ${slackTestResult === 'success' ? 'text-green-400' : 'text-red-400'}`}>
                  {slackTestResult === 'success' ? 'Test Successful' : 'Test Failed'}
                </p>
                <p className="text-sm text-gray-300 mt-1">{slackTestMessage}</p>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={handleTestSlack}
              disabled={!slackConfig.slack_enabled || !slackConfig.slack_webhook_url || slackTesting}
              className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {slackTesting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Testing...
                </>
              ) : (
                'Test Connection'
              )}
            </button>
            <button
              onClick={handleSaveSlackConfig}
              className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors flex items-center justify-center gap-2"
            >
              {slackSaved ? (
                <>
                  <Check className="w-4 h-4" />
                  Saved!
                </>
              ) : (
                <>
                  <MessageSquare className="w-4 h-4" />
                  Save Slack Settings
                </>
              )}
            </button>
          </div>
        </div>

        {/* Map Basemap (CARTO) Section */}
        <div className="mb-6 p-4 bg-gray-750 rounded-lg border border-gray-700">
          <div className="flex items-center gap-2 mb-3">
            <Map className="w-5 h-5 text-teal-500" />
            <h3 className="text-sm font-semibold text-white">Map Basemap (CARTO)</h3>
          </div>
          <p className="text-sm text-gray-400 mb-4">
            Authenticate map tile requests with your CARTO API key and choose the basemap style.
            Saved values apply to everyone and override the build-time defaults
            {ENV_CARTO_API_KEY ? ' (a key is currently set via environment)' : ''}.
          </p>

          <div className="mb-3">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              CARTO API Key
            </label>
            <input
              type="password"
              value={cartoConfig.carto_api_key || ''}
              onChange={(e) => setCartoConfig({ ...cartoConfig, carto_api_key: e.target.value || null })}
              placeholder={ENV_CARTO_API_KEY ? 'Using key from environment — enter to override' : 'Paste your CARTO API key / access token'}
              autoComplete="off"
              className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 font-mono text-sm"
            />
            <p className="text-xs text-gray-400 mt-1">
              Sent as <code>?key=</code> on every tile request (get one at carto.com/basemaps/apikey). Without it CARTO watermarks tiles with &quot;API KEY REQUIRED&quot;.
            </p>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Basemap Style
            </label>
            <select
              value={cartoConfig.carto_basemap || ''}
              onChange={(e) => setCartoConfig({ ...cartoConfig, carto_basemap: e.target.value || null })}
              className="w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 text-sm"
            >
              <option value="">Default ({ENV_CARTO_BASEMAP})</option>
              {CARTO_BASEMAP_STYLES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          {cartoError && (
            <div className="mb-4 p-3 rounded-lg flex items-start gap-3 bg-red-900/30 border border-red-700">
              <X className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-400">{cartoError}</p>
            </div>
          )}

          <button
            onClick={handleSaveCartoConfig}
            className="w-full px-4 py-2 bg-teal-600 text-white rounded-md hover:bg-teal-700 transition-colors flex items-center justify-center gap-2"
          >
            {cartoSaved ? (
              <>
                <Check className="w-4 h-4" />
                Saved — map updated
              </>
            ) : (
              <>
                <Map className="w-4 h-4" />
                Save Basemap Settings
              </>
            )}
          </button>
        </div>

        {/* Cloudera Services Section */}
        <div className="mb-6 p-4 bg-gray-750 rounded-lg border border-gray-700">
          <div className="flex items-center gap-2 mb-3">
            <Cloud className="w-5 h-5 text-orange-500" />
            <h3 className="text-sm font-semibold text-white">Cloudera Data Platform Services</h3>
          </div>
          <p className="text-sm text-gray-400 mb-4">
            Configure connections to Cloudera services: NiFi, Kafka, Spark, Kudu, Iceberg, Atlas, Airflow, CML, and CDW.
          </p>
          <button
            onClick={() => setShowClouderaServices(true)}
            className="w-full px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 transition-colors flex items-center justify-center gap-2"
          >
            <Cloud className="w-4 h-4" />
            Configure Cloudera Services
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-1">
            <button
              onClick={handleTestConnection}
              disabled={!config.enabled || testing}
              className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {testing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Testing...
                </>
              ) : (
                'Test Connection'
              )}
            </button>
            {testing && testMessage && (
              <span className="text-xs text-gray-400">{testMessage}</span>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!config.enabled}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {saved && <Check className="w-4 h-4" />}
              {saved ? 'Saved!' : 'Save & Apply'}
            </button>
          </div>
        </div>
      </div>

      {/* Cloudera Services Panel */}
      {showClouderaServices && (
        <ClouderaServicesPanel onClose={() => setShowClouderaServices(false)} />
      )}
    </div>
  );
});

AISettingsPanel.displayName = 'AISettingsPanel';

export default AISettingsPanel;
