import { memo, useState, useEffect } from 'react';
import { systemSettingsService } from '@/services/systemSettingsService';
import {
  Settings,
  Check,
  X,
  AlertCircle,
  Loader2,
  Cloud,
  Database,
  Workflow,
  Cpu,
  BarChart3,
  Shield,
  Server,
  Brain,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface ClouderaServicesConfig {
  // NiFi
  nifi_enabled: boolean;
  nifi_url: string;
  nifi_username: string;
  nifi_password: string;
  nifi_status: string;
  // Kafka
  kafka_enabled: boolean;
  kafka_bootstrap_servers: string;
  kafka_topics: string[];
  kafka_security_protocol: string;
  kafka_sasl_mechanism: string;
  kafka_username: string;
  kafka_password: string;
  kafka_status: string;
  // Spark
  spark_enabled: boolean;
  spark_master_url: string;
  spark_app_name: string;
  spark_executor_memory: string;
  spark_executor_cores: number;
  spark_status: string;
  // Kudu
  kudu_enabled: boolean;
  kudu_master_addresses: string;
  kudu_table_prefix: string;
  kudu_status: string;
  // Iceberg
  iceberg_enabled: boolean;
  iceberg_catalog_url: string;
  iceberg_catalog_type: string;
  iceberg_warehouse: string;
  iceberg_namespace: string;
  iceberg_status: string;
  // Atlas
  atlas_enabled: boolean;
  atlas_url: string;
  atlas_username: string;
  atlas_password: string;
  atlas_status: string;
  // Airflow
  airflow_enabled: boolean;
  airflow_url: string;
  airflow_username: string;
  airflow_password: string;
  airflow_status: string;
  // CML
  cml_enabled: boolean;
  cml_workspace_url: string;
  cml_api_key: string;
  cml_project_name: string;
  cml_status: string;
  // CDW
  cdw_enabled: boolean;
  cdw_jdbc_url: string;
  cdw_username: string;
  cdw_password: string;
  cdw_status: string;
  // S3 / object storage — edge pcap staging
  s3_staging_enabled: boolean;
  s3_staging_endpoint_url: string;
  s3_staging_access_key: string;
  s3_staging_secret_key: string;
  s3_staging_bucket: string;
  s3_staging_region: string;
  s3_staging_prefix: string;
  s3_staging_status: string;
}

interface ClouderaServicesPanelProps {
  onClose: () => void;
}

type ServiceKey = 'nifi' | 'kafka' | 'spark' | 'kudu' | 'iceberg' | 'atlas' | 'airflow' | 'cml' | 'cdw';

interface ServiceConfig {
  key: ServiceKey;
  name: string;
  description: string;
  icon: React.ReactNode;
  color: string;
}

const SERVICES: ServiceConfig[] = [
  { key: 'nifi', name: 'Apache NiFi', description: 'Data ingestion and flow management', icon: <Workflow className="w-5 h-5" />, color: 'text-blue-400' },
  { key: 'kafka', name: 'Apache Kafka', description: 'Real-time message streaming', icon: <Server className="w-5 h-5" />, color: 'text-orange-400' },
  { key: 'spark', name: 'Apache Spark', description: 'Stream processing and analytics', icon: <Cpu className="w-5 h-5" />, color: 'text-yellow-400' },
  { key: 'kudu', name: 'Apache Kudu', description: 'Real-time columnar storage', icon: <Database className="w-5 h-5" />, color: 'text-green-400' },
  { key: 'iceberg', name: 'Apache Iceberg', description: 'Data lakehouse table format', icon: <Database className="w-5 h-5" />, color: 'text-cyan-400' },
  { key: 'atlas', name: 'Apache Atlas', description: 'Data governance and lineage', icon: <Shield className="w-5 h-5" />, color: 'text-purple-400' },
  { key: 'airflow', name: 'Apache Airflow', description: 'Workflow orchestration', icon: <Workflow className="w-5 h-5" />, color: 'text-teal-400' },
  { key: 'cml', name: 'Cloudera ML', description: 'Machine learning platform', icon: <Brain className="w-5 h-5" />, color: 'text-pink-400' },
  { key: 'cdw', name: 'Cloudera Data Warehouse', description: 'Analytics and BI', icon: <BarChart3 className="w-5 h-5" />, color: 'text-indigo-400' },
];

const defaultConfig: ClouderaServicesConfig = {
  nifi_enabled: false, nifi_url: '', nifi_username: '', nifi_password: '', nifi_status: 'disconnected',
  kafka_enabled: false, kafka_bootstrap_servers: '', kafka_topics: [], kafka_security_protocol: 'PLAINTEXT', kafka_sasl_mechanism: '', kafka_username: '', kafka_password: '', kafka_status: 'disconnected',
  spark_enabled: false, spark_master_url: '', spark_app_name: 'TelcoSelfHealing', spark_executor_memory: '2g', spark_executor_cores: 2, spark_status: 'disconnected',
  kudu_enabled: false, kudu_master_addresses: '', kudu_table_prefix: 'telco_', kudu_status: 'disconnected',
  iceberg_enabled: false, iceberg_catalog_url: '', iceberg_catalog_type: 'hive', iceberg_warehouse: '', iceberg_namespace: 'telco_data', iceberg_status: 'disconnected',
  atlas_enabled: false, atlas_url: '', atlas_username: '', atlas_password: '', atlas_status: 'disconnected',
  airflow_enabled: false, airflow_url: '', airflow_username: '', airflow_password: '', airflow_status: 'disconnected',
  cml_enabled: false, cml_workspace_url: '', cml_api_key: '', cml_project_name: '', cml_status: 'disconnected',
  cdw_enabled: false, cdw_jdbc_url: '', cdw_username: '', cdw_password: '', cdw_status: 'disconnected',
  s3_staging_enabled: false, s3_staging_endpoint_url: '', s3_staging_access_key: '', s3_staging_secret_key: '', s3_staging_bucket: '', s3_staging_region: '', s3_staging_prefix: 'edge-captures', s3_staging_status: 'disconnected',
};

const ClouderaServicesPanel = memo(({ onClose }: ClouderaServicesPanelProps) => {
  const [config, setConfig] = useState<ClouderaServicesConfig>(defaultConfig);
  const [expandedService, setExpandedService] = useState<ServiceKey | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState<ServiceKey | null>(null);
  const [testResults, setTestResults] = useState<Record<ServiceKey, { status: string; message: string } | null>>({
    nifi: null, kafka: null, spark: null, kudu: null, iceberg: null, atlas: null, airflow: null, cml: null, cdw: null,
  });
  const [loading, setLoading] = useState(true);
  const [testingS3, setTestingS3] = useState(false);
  const [s3Result, setS3Result] = useState<{ ok: boolean; message: string } | null>(null);

  // Load config on mount
  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const backendUrl = systemSettingsService.getBackendUrl();
      const response = await fetch(`${backendUrl}/api/v1/cloudera/services`);
      if (response.ok) {
        const data = await response.json();
        setConfig({ ...defaultConfig, ...data });
      }
    } catch (error) {
      console.log('Cloudera services not configured yet');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const backendUrl = systemSettingsService.getBackendUrl();
      const response = await fetch(`${backendUrl}/api/v1/cloudera/services`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (response.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      }
    } catch (error) {
      console.error('Failed to save Cloudera services config:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async (serviceKey: ServiceKey) => {
    setTesting(serviceKey);
    setTestResults((prev) => ({ ...prev, [serviceKey]: null }));
    try {
      const backendUrl = systemSettingsService.getBackendUrl();
      const response = await fetch(`${backendUrl}/api/v1/cloudera/services/test/${serviceKey}`, {
        method: 'POST',
      });
      const result = await response.json();
      setTestResults((prev) => ({ ...prev, [serviceKey]: result }));
      // Reload config to get updated status
      await loadConfig();
    } catch (error) {
      setTestResults((prev) => ({ ...prev, [serviceKey]: { status: 'error', message: 'Request failed' } }));
    } finally {
      setTesting(null);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusColors: Record<string, string> = {
      connected: 'bg-green-600 text-white',
      configured: 'bg-blue-600 text-white',
      disconnected: 'bg-gray-600 text-gray-300',
      error: 'bg-red-600 text-white',
    };
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[status] || statusColors.disconnected}`}>
        {status}
      </span>
    );
  };

  const setField = (field: keyof ClouderaServicesConfig, value: string | boolean) =>
    setConfig((prev) => ({ ...prev, [field]: value }));

  const testS3 = async () => {
    setTestingS3(true);
    setS3Result(null);
    try {
      // Persist first so the backend probes the just-entered config.
      await handleSave();
      const backendUrl = systemSettingsService.getBackendUrl();
      const apiKey = import.meta.env.VITE_API_KEY || 'dev-api-key-change-me';
      const response = await fetch(`${backendUrl}/api/v1/cloudera/services/test/s3`, {
        method: 'POST',
        headers: { 'X-API-Key': apiKey },
      });
      setS3Result(await response.json());
    } catch {
      setS3Result({ ok: false, message: 'Request failed' });
    } finally {
      setTestingS3(false);
    }
  };

  const updateServiceConfig = (serviceKey: ServiceKey, field: string, value: string | boolean | number | string[]) => {
    setConfig((prev) => ({
      ...prev,
      [`${serviceKey}_${field}`]: value,
    }));
  };

  const renderServiceFields = (serviceKey: ServiceKey) => {
    const inputClass = 'w-full bg-gray-700 text-white rounded-md px-3 py-2 border border-gray-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm font-mono';
    const labelClass = 'block text-sm font-medium text-gray-300 mb-1';

    switch (serviceKey) {
      case 'nifi':
        return (
          <>
            <div>
              <label className={labelClass}>NiFi URL</label>
              <input
                type="text"
                value={config.nifi_url}
                onChange={(e) => updateServiceConfig('nifi', 'url', e.target.value)}
                placeholder="https://nifi.example.com:8443"
                className={inputClass}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>Username</label>
                <input
                  type="text"
                  value={config.nifi_username}
                  onChange={(e) => updateServiceConfig('nifi', 'username', e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Password</label>
                <input
                  type="password"
                  value={config.nifi_password}
                  onChange={(e) => updateServiceConfig('nifi', 'password', e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>
          </>
        );

      case 'kafka':
        return (
          <>
            <div>
              <label className={labelClass}>Bootstrap Servers</label>
              <input
                type="text"
                value={config.kafka_bootstrap_servers}
                onChange={(e) => updateServiceConfig('kafka', 'bootstrap_servers', e.target.value)}
                placeholder="broker1:9092,broker2:9092"
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Topics (comma-separated)</label>
              <input
                type="text"
                value={config.kafka_topics?.join(', ') || ''}
                onChange={(e) => updateServiceConfig('kafka', 'topics', e.target.value.split(',').map((t) => t.trim()))}
                placeholder="node-kpis, alerts, actions"
                className={inputClass}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>Security Protocol</label>
                <select
                  value={config.kafka_security_protocol}
                  onChange={(e) => updateServiceConfig('kafka', 'security_protocol', e.target.value)}
                  className={inputClass}
                >
                  <option value="PLAINTEXT">PLAINTEXT</option>
                  <option value="SSL">SSL</option>
                  <option value="SASL_SSL">SASL_SSL</option>
                  <option value="SASL_PLAINTEXT">SASL_PLAINTEXT</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>SASL Mechanism</label>
                <select
                  value={config.kafka_sasl_mechanism}
                  onChange={(e) => updateServiceConfig('kafka', 'sasl_mechanism', e.target.value)}
                  className={inputClass}
                >
                  <option value="">None</option>
                  <option value="PLAIN">PLAIN</option>
                  <option value="SCRAM-SHA-256">SCRAM-SHA-256</option>
                  <option value="GSSAPI">GSSAPI (Kerberos)</option>
                </select>
              </div>
            </div>
            {config.kafka_security_protocol.includes('SASL') && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>Username</label>
                  <input
                    type="text"
                    value={config.kafka_username}
                    onChange={(e) => updateServiceConfig('kafka', 'username', e.target.value)}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Password</label>
                  <input
                    type="password"
                    value={config.kafka_password}
                    onChange={(e) => updateServiceConfig('kafka', 'password', e.target.value)}
                    className={inputClass}
                  />
                </div>
              </div>
            )}
          </>
        );

      case 'spark':
        return (
          <>
            <div>
              <label className={labelClass}>Master URL</label>
              <input
                type="text"
                value={config.spark_master_url}
                onChange={(e) => updateServiceConfig('spark', 'master_url', e.target.value)}
                placeholder="spark://master:7077 or yarn"
                className={inputClass}
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={labelClass}>App Name</label>
                <input
                  type="text"
                  value={config.spark_app_name}
                  onChange={(e) => updateServiceConfig('spark', 'app_name', e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Executor Memory</label>
                <input
                  type="text"
                  value={config.spark_executor_memory}
                  onChange={(e) => updateServiceConfig('spark', 'executor_memory', e.target.value)}
                  placeholder="2g"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Executor Cores</label>
                <input
                  type="number"
                  value={config.spark_executor_cores}
                  onChange={(e) => updateServiceConfig('spark', 'executor_cores', parseInt(e.target.value))}
                  min={1}
                  max={32}
                  className={inputClass}
                />
              </div>
            </div>
          </>
        );

      case 'kudu':
        return (
          <>
            <div>
              <label className={labelClass}>Master Addresses</label>
              <input
                type="text"
                value={config.kudu_master_addresses}
                onChange={(e) => updateServiceConfig('kudu', 'master_addresses', e.target.value)}
                placeholder="kudu-master1:7051,kudu-master2:7051"
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Table Prefix</label>
              <input
                type="text"
                value={config.kudu_table_prefix}
                onChange={(e) => updateServiceConfig('kudu', 'table_prefix', e.target.value)}
                placeholder="telco_"
                className={inputClass}
              />
            </div>
          </>
        );

      case 'iceberg':
        return (
          <>
            <div>
              <label className={labelClass}>Catalog URL</label>
              <input
                type="text"
                value={config.iceberg_catalog_url}
                onChange={(e) => updateServiceConfig('iceberg', 'catalog_url', e.target.value)}
                placeholder="thrift://hive-metastore:9083"
                className={inputClass}
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={labelClass}>Catalog Type</label>
                <select
                  value={config.iceberg_catalog_type}
                  onChange={(e) => updateServiceConfig('iceberg', 'catalog_type', e.target.value)}
                  className={inputClass}
                >
                  <option value="hive">Hive</option>
                  <option value="hadoop">Hadoop</option>
                  <option value="rest">REST</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>Warehouse</label>
                <input
                  type="text"
                  value={config.iceberg_warehouse}
                  onChange={(e) => updateServiceConfig('iceberg', 'warehouse', e.target.value)}
                  placeholder="s3://bucket/warehouse"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Namespace</label>
                <input
                  type="text"
                  value={config.iceberg_namespace}
                  onChange={(e) => updateServiceConfig('iceberg', 'namespace', e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>
          </>
        );

      case 'atlas':
        return (
          <>
            <div>
              <label className={labelClass}>Atlas URL</label>
              <input
                type="text"
                value={config.atlas_url}
                onChange={(e) => updateServiceConfig('atlas', 'url', e.target.value)}
                placeholder="https://atlas.example.com:21443"
                className={inputClass}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>Username</label>
                <input
                  type="text"
                  value={config.atlas_username}
                  onChange={(e) => updateServiceConfig('atlas', 'username', e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Password</label>
                <input
                  type="password"
                  value={config.atlas_password}
                  onChange={(e) => updateServiceConfig('atlas', 'password', e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>
          </>
        );

      case 'airflow':
        return (
          <>
            <div>
              <label className={labelClass}>Airflow URL</label>
              <input
                type="text"
                value={config.airflow_url}
                onChange={(e) => updateServiceConfig('airflow', 'url', e.target.value)}
                placeholder="https://airflow.example.com:8080"
                className={inputClass}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>Username</label>
                <input
                  type="text"
                  value={config.airflow_username}
                  onChange={(e) => updateServiceConfig('airflow', 'username', e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Password</label>
                <input
                  type="password"
                  value={config.airflow_password}
                  onChange={(e) => updateServiceConfig('airflow', 'password', e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>
          </>
        );

      case 'cml':
        return (
          <>
            <div>
              <label className={labelClass}>Workspace URL</label>
              <input
                type="text"
                value={config.cml_workspace_url}
                onChange={(e) => updateServiceConfig('cml', 'workspace_url', e.target.value)}
                placeholder="https://ml-xxxxx.cloudera.site"
                className={inputClass}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>API Key</label>
                <input
                  type="password"
                  value={config.cml_api_key}
                  onChange={(e) => updateServiceConfig('cml', 'api_key', e.target.value)}
                  placeholder="Your Cloudera ML API key"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Project Name</label>
                <input
                  type="text"
                  value={config.cml_project_name}
                  onChange={(e) => updateServiceConfig('cml', 'project_name', e.target.value)}
                  placeholder="telco-self-healing"
                  className={inputClass}
                />
              </div>
            </div>
          </>
        );

      case 'cdw':
        return (
          <>
            <div>
              <label className={labelClass}>JDBC URL</label>
              <input
                type="text"
                value={config.cdw_jdbc_url}
                onChange={(e) => updateServiceConfig('cdw', 'jdbc_url', e.target.value)}
                placeholder="jdbc:hive2://cdw.example.com:10000/default"
                className={inputClass}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>Username</label>
                <input
                  type="text"
                  value={config.cdw_username}
                  onChange={(e) => updateServiceConfig('cdw', 'username', e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Password</label>
                <input
                  type="password"
                  value={config.cdw_password}
                  onChange={(e) => updateServiceConfig('cdw', 'password', e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>
          </>
        );

      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[1100]">
        <div className="bg-gray-800 rounded-lg p-8">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto" />
          <p className="text-gray-400 mt-2">Loading configuration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[1100]">
      <div className="bg-gray-800 rounded-lg shadow-xl border border-gray-700 p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Cloud className="w-6 h-6 text-orange-500" />
            <div>
              <h2 className="text-xl font-bold text-white">Cloudera Data Platform Services</h2>
              <p className="text-sm text-gray-400">Configure connections to CDP services</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Summary */}
        <div className="mb-6 p-4 bg-gray-750 rounded-lg border border-gray-700">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-sm text-gray-300">
                {SERVICES.filter((s) => config[`${s.key}_enabled` as keyof ClouderaServicesConfig]).length} enabled
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <span className="text-sm text-gray-300">
                {SERVICES.filter((s) => config[`${s.key}_status` as keyof ClouderaServicesConfig] === 'connected').length} connected
              </span>
            </div>
          </div>
        </div>

        {/* Services List */}
        <div className="space-y-3">
          {SERVICES.map((service) => {
            const isExpanded = expandedService === service.key;
            const isEnabled = config[`${service.key}_enabled` as keyof ClouderaServicesConfig] as boolean;
            const status = config[`${service.key}_status` as keyof ClouderaServicesConfig] as string;
            const testResult = testResults[service.key];

            return (
              <div key={service.key} className="bg-gray-750 rounded-lg border border-gray-700 overflow-hidden">
                {/* Service Header */}
                <div
                  className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-700 transition-colors"
                  onClick={() => setExpandedService(isExpanded ? null : service.key)}
                >
                  <div className="flex items-center gap-3">
                    <div className={service.color}>{service.icon}</div>
                    <div>
                      <h3 className="text-white font-medium">{service.name}</h3>
                      <p className="text-xs text-gray-400">{service.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {getStatusBadge(status)}
                    <label
                      className="relative inline-flex items-center cursor-pointer"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <input
                        type="checkbox"
                        checked={isEnabled}
                        onChange={(e) => {
                          e.stopPropagation();
                          updateServiceConfig(service.key, 'enabled', e.target.checked);
                        }}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-gray-600 peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600" />
                    </label>
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    )}
                  </div>
                </div>

                {/* Service Configuration */}
                {isExpanded && (
                  <div className="p-4 border-t border-gray-700 space-y-3">
                    {renderServiceFields(service.key)}

                    {/* Test Result */}
                    {testResult && (
                      <div
                        className={`p-3 rounded-lg flex items-start gap-2 ${
                          testResult.status === 'connected' || testResult.status === 'configured'
                            ? 'bg-green-900/30 border border-green-700'
                            : testResult.status === 'error'
                            ? 'bg-red-900/30 border border-red-700'
                            : 'bg-gray-700 border border-gray-600'
                        }`}
                      >
                        {testResult.status === 'connected' || testResult.status === 'configured' ? (
                          <Check className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                        ) : testResult.status === 'error' ? (
                          <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
                        )}
                        <p className="text-sm text-gray-300">{testResult.message}</p>
                      </div>
                    )}

                    {/* Test Connection Button */}
                    <div className="flex justify-end">
                      <button
                        onClick={() => handleTestConnection(service.key)}
                        disabled={!isEnabled || testing === service.key}
                        className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 text-sm"
                      >
                        {testing === service.key ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Testing...
                          </>
                        ) : (
                          'Test Connection'
                        )}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* S3 / object storage — edge pcap staging */}
        <div className="mt-6 p-4 bg-gray-800 border border-gray-700 rounded-lg">
          <div className="flex items-center gap-2 mb-1">
            <Database className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white">S3 / Object Storage — edge pcap staging</h3>
          </div>
          <p className="text-xs text-gray-500 mb-3">
            Where the edge headend stages suspect captures for the primary DC to retrieve. Leave the
            bucket blank to stage on local disk — the edge flow works either way. An endpoint URL
            enables MinIO / Cloudera Ozone (path-style); blank endpoint targets AWS S3.
          </p>
          <div className="grid sm:grid-cols-2 gap-3">
            <label className="text-xs text-gray-400">
              Bucket (blank = local disk)
              <input
                value={config.s3_staging_bucket}
                onChange={(e) => setField('s3_staging_bucket', e.target.value)}
                placeholder="my-edge-captures"
                className="mt-1 w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded text-sm"
              />
            </label>
            <label className="text-xs text-gray-400">
              Endpoint URL (blank = AWS)
              <input
                value={config.s3_staging_endpoint_url}
                onChange={(e) => setField('s3_staging_endpoint_url', e.target.value)}
                placeholder="https://minio.example:9000"
                className="mt-1 w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded text-sm"
              />
            </label>
            <label className="text-xs text-gray-400">
              Region
              <input
                value={config.s3_staging_region}
                onChange={(e) => setField('s3_staging_region', e.target.value)}
                placeholder="us-east-1"
                className="mt-1 w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded text-sm"
              />
            </label>
            <label className="text-xs text-gray-400">
              Prefix
              <input
                value={config.s3_staging_prefix}
                onChange={(e) => setField('s3_staging_prefix', e.target.value)}
                placeholder="edge-captures"
                className="mt-1 w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded text-sm"
              />
            </label>
            <label className="text-xs text-gray-400">
              Access key
              <input
                type="password"
                value={config.s3_staging_access_key}
                onChange={(e) => setField('s3_staging_access_key', e.target.value)}
                className="mt-1 w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded text-sm"
              />
            </label>
            <label className="text-xs text-gray-400">
              Secret key
              <input
                type="password"
                value={config.s3_staging_secret_key}
                onChange={(e) => setField('s3_staging_secret_key', e.target.value)}
                className="mt-1 w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded text-sm"
              />
            </label>
          </div>
          <div className="mt-3 flex items-center gap-3">
            <button
              onClick={testS3}
              disabled={testingS3}
              className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded text-sm disabled:opacity-50 inline-flex items-center gap-1.5"
            >
              {testingS3 ? <Loader2 className="w-4 h-4 animate-spin" /> : <Server className="w-4 h-4" />}
              Test S3 connection
            </button>
            {s3Result && (
              <span className={`text-xs ${s3Result.ok ? 'text-emerald-400' : 'text-red-400'}`}>
                {s3Result.message}
              </span>
            )}
          </div>
        </div>

        {/* Info Box */}
        <div className="mt-6 p-3 bg-blue-900/20 border border-blue-700 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-gray-300">
            <p className="font-medium text-blue-400 mb-1">Data Integration</p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>NiFi ingests node data and streams to Kafka</li>
              <li>Spark processes Kafka streams for real-time analytics</li>
              <li>Kudu stores hot data, Iceberg stores historical data</li>
              <li>Atlas provides governance and data lineage</li>
              <li>Airflow orchestrates data pipelines</li>
              <li>CML runs AI models for predictions</li>
            </ul>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : saved ? (
              <Check className="w-4 h-4" />
            ) : (
              <Settings className="w-4 h-4" />
            )}
            {saved ? 'Saved!' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  );
});

ClouderaServicesPanel.displayName = 'ClouderaServicesPanel';

export default ClouderaServicesPanel;
