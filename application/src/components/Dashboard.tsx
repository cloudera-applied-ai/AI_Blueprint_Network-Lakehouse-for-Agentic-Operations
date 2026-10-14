import { useState, lazy, Suspense } from 'react';
import { Activity, Settings, Loader2, Pause, Play } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './shared/Tabs';
import BackendSetup from './BackendSetup';

// Lazy load tab components for faster initial render
const MapDashboard = lazy(() => import('./dashboard/MapDashboard'));
const ArchitectureView = lazy(() => import('./dashboard/ArchitectureView'));
const NOCOperationsView = lazy(() => import('./dashboard/NOCOperationsView'));
const CoreNetworkView = lazy(() => import('./dashboard/CoreNetworkView'));
const DigitalTwinView = lazy(() => import('./dashboard/DigitalTwinView'));
const ExecutiveView = lazy(() => import('./dashboard/ExecutiveView'));
const ConfigManagementView = lazy(() => import('./dashboard/ConfigManagementView'));
const CustomerIntelligenceView = lazy(() => import('./dashboard/CustomerIntelligenceView'));
const PacketAnalysisView = lazy(() => import('./dashboard/PacketAnalysisView'));
const EdgeOperationsView = lazy(() => import('./dashboard/EdgeOperationsView'));
const AISettingsPanel = lazy(() => import('./panels/AISettingsPanel'));

// Loading fallback for lazy-loaded components
const TabLoadingFallback = () => (
  <div className="flex items-center justify-center h-64 bg-gray-800 rounded-lg">
    <div className="flex items-center gap-3 text-gray-400">
      <Loader2 className="w-6 h-6 animate-spin" />
      <span>Loading view...</span>
    </div>
  </div>
);
import { TimeRangeSelector, type TimeRange, timeRangeToHours } from './shared/TimeRangeSelector';
import {
  clearAllInMemoryData,
  loadFromBackend,
  isBackendEnabled,
  fetchHistoricalKPIs,
  getFiberNodes,
  insertAntennaSensors,
  insertWeatherData,
  insertEnvSensors,
  insertEquipmentSensors,
} from '@/services/memoryStore';
import { generateSensorDataBatch } from '@/services/sensorDataGenerator';
import { systemSettingsService } from '@/services/systemSettingsService';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataRefresh } from '@/hooks/useDataRefresh';
import { useSystemPause } from '@/hooks/useSystemPause';

const Dashboard = () => {
  const {
    needsSetup,
    loading,
    loadingMessage,
    error,
    nodes,
    handleBackendConfigured,
    setLoading,
    setLoadingMessage,
    setNodes,
    setError,
    setNeedsSetup,
  } = useBackendConnection();

  const {
    archMetrics,
    alerts,
    actions,
    aiInsights,
    aiActionPlans,
    crewDispatches,
  } = useDataRefresh(loading, nodes, setNodes);

  const {
    paused: systemPaused,
    loading: pauseLoading,
    togglePause: handleTogglePause,
  } = useSystemPause(loading);

  const [showSettings, setShowSettings] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>('1h');
  const [timeRangeLoading, setTimeRangeLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [packetCaptureId, setPacketCaptureId] = useState<string | null>(null);

  // Cross-navigation: Edge Operations → open the resulting capture in Packet Analysis.
  const openCapture = (captureId: string) => {
    setPacketCaptureId(captureId);
    setActiveTab('packet-analysis');
  };

  // Handle time range changes - fetch historical data on-demand
  const handleTimeRangeChange = async (newRange: TimeRange) => {
    if (newRange === timeRange) return;

    setTimeRange(newRange);

    // Only fetch more data if expanding the time range
    const newHours = timeRangeToHours(newRange);
    const currentHours = timeRangeToHours(timeRange);

    if (newHours > currentHours && isBackendEnabled()) {
      setTimeRangeLoading(true);
      console.log(`Time range expanded from ${timeRange} to ${newRange}, fetching more data...`);

      try {
        await fetchHistoricalKPIs(newHours);
      } catch (error) {
        console.error('Failed to fetch historical data:', error);
      } finally {
        setTimeRangeLoading(false);
      }
    }
  };

  // Regenerate all data (60 days) via backend
  const handleRegenerateAllData = async () => {
    if (!confirm('This will delete all existing data and regenerate 60 days of historical data via the backend. This may take a few minutes. Continue?')) {
      return;
    }

    setRegenerating(true);

    try {
      const { generateNodes, generateHistoricalKPIs } = await import('@/services/apiClient');

      clearAllInMemoryData();

      setLoadingMessage('Regenerating node data on backend...');

      await generateNodes(10000, undefined, true);

      setLoadingMessage('Generating 60 days of historical KPI data on backend... This may take a few minutes.');

      await generateHistoricalKPIs(60, 60);

      setLoadingMessage('Loading fresh data from backend...');

      await loadFromBackend();
      const freshNodes = await getFiberNodes();
      setNodes(freshNodes);

      setLoadingMessage('Generating sensor data for all nodes...');
      const sensorBatch = generateSensorDataBatch(freshNodes);
      insertAntennaSensors(sensorBatch.antennaSensors);
      insertWeatherData(sensorBatch.weatherData);
      insertEnvSensors(sensorBatch.environmentalSensors);
      insertEquipmentSensors(sensorBatch.equipmentSensors);

      setLoadingMessage('Data regeneration complete!');
      console.log('All data regenerated successfully via backend');

      setTimeout(() => {
        setRegenerating(false);
        setLoadingMessage('');
      }, 1500);

    } catch (error) {
      console.error('Error regenerating data:', error);
      setError('Failed to regenerate data. Is the backend running?');
      setRegenerating(false);
    }
  };

  if (needsSetup) {
    return <BackendSetup onConfigured={handleBackendConfigured} />;
  }

  if (loading || regenerating) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-300 text-lg mb-2">
            {regenerating ? 'Regenerating Data...' : 'Network Data Lakehouse'}
          </p>
          <p className="text-gray-400 text-sm mb-4">{loadingMessage}</p>
          <p className="text-gray-600 text-xs">
            Loading network data from backend...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center text-red-400">
          <p className="text-lg font-semibold">{error}</p>
          <p className="text-gray-500 text-sm mt-2">
            Current backend URL: {systemSettingsService.getBackendUrl() || '(relative — no URL configured)'}
          </p>
          <div className="flex gap-3 justify-center mt-4">
            <button
              onClick={() => {
                systemSettingsService.saveBackendUrlLocally('');
                setNeedsSetup(true);
                setError(null);
                setLoading(true);
              }}
              className="px-4 py-2 bg-gray-700 text-white rounded hover:bg-gray-600"
            >
              Change URL
            </button>
            <button
              onClick={() => setShowSettings(true)}
              className="px-4 py-2 bg-gray-700 text-white rounded hover:bg-gray-600 flex items-center gap-2"
            >
              <Settings className="w-4 h-4" />
              Settings
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Retry
            </button>
          </div>
        </div>
        {showSettings && (
          <Suspense fallback={<TabLoadingFallback />}>
            <AISettingsPanel
              onClose={() => setShowSettings(false)}
              onRegenerateData={handleRegenerateAllData}
            />
          </Suspense>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-900">
      {/* Cloudera 2025 brand chrome: orange accent rule + white header, indigo headline */}
      <header className="bg-white shadow-sm border-b border-gray-600">
        <div className="h-2 bg-brand-orange" />
        <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-brand-indigo tracking-tight">
                {selectedProvider ? `${selectedProvider} Data Lakehouse` : 'Network Data Lakehouse'}
              </h1>
              <p className="text-sm text-brand-blue mt-1">
                AI-Powered Network Monitoring & Automated Remediation
              </p>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-400">
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Activity className="w-4 h-4 text-green-500" />
                  <div className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                </div>
                <span className="font-medium text-green-500">Live</span>
              </div>
              <span className="text-gray-600">•</span>
              <span className="text-gray-300">{nodes.length} Nodes</span>
              <span className="text-gray-600">•</span>
              <TimeRangeSelector
                value={timeRange}
                onChange={handleTimeRangeChange}
                loading={timeRangeLoading}
              />
              {/* Pause/Resume System Button */}
              <button
                onClick={handleTogglePause}
                disabled={pauseLoading}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors ${
                  systemPaused
                    ? 'bg-yellow-600 hover:bg-yellow-500 text-white'
                    : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                } ${pauseLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                title={systemPaused ? 'Resume data generation & AI analysis' : 'Pause data generation & AI analysis (reduce GPU load)'}
              >
                {pauseLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : systemPaused ? (
                  <Play className="w-4 h-4" />
                ) : (
                  <Pause className="w-4 h-4" />
                )}
                <span className="text-sm font-medium">
                  {systemPaused ? 'Resume' : 'Pause'}
                </span>
              </button>
              <button
                onClick={() => setShowSettings(true)}
                className="p-2 text-gray-400 hover:text-white transition-colors rounded-md hover:bg-gray-700"
                title="AI Agent Settings"
              >
                <Settings className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 w-full max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Tabs defaultValue="dashboard" value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="mb-6">
            <TabsTrigger value="dashboard">Global Network Dashboard</TabsTrigger>
            <TabsTrigger value="executive">Executive Summary</TabsTrigger>
            <TabsTrigger value="digital-twin">Digital Twin</TabsTrigger>
            <TabsTrigger value="core-network">Cable Infrastructure</TabsTrigger>
            <TabsTrigger value="customer-intel">Customer Intelligence</TabsTrigger>
            <TabsTrigger value="operations">Operations Center</TabsTrigger>
            <TabsTrigger value="packet-analysis">Packet Analysis</TabsTrigger>
            <TabsTrigger value="edge-ops">Edge Operations</TabsTrigger>
            <TabsTrigger value="architecture">Architecture & Data Flow</TabsTrigger>
            <TabsTrigger value="config-management">Config Management</TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard">
            <Suspense fallback={<TabLoadingFallback />}>
              <MapDashboard nodes={nodes} onProviderChange={setSelectedProvider} />
            </Suspense>
          </TabsContent>

          <TabsContent value="executive">
            <Suspense fallback={<TabLoadingFallback />}>
              <ExecutiveView />
            </Suspense>
          </TabsContent>

          <TabsContent value="digital-twin">
            <Suspense fallback={<TabLoadingFallback />}>
              <DigitalTwinView />
            </Suspense>
          </TabsContent>

          <TabsContent value="core-network">
            <Suspense fallback={<TabLoadingFallback />}>
              <CoreNetworkView />
            </Suspense>
          </TabsContent>

          <TabsContent value="customer-intel">
            <Suspense fallback={<TabLoadingFallback />}>
              <CustomerIntelligenceView />
            </Suspense>
          </TabsContent>

          <TabsContent value="operations">
            <Suspense fallback={<TabLoadingFallback />}>
              <NOCOperationsView
                alerts={alerts}
                actions={actions}
                nodes={nodes}
                aiInsights={aiInsights}
                aiActionPlans={aiActionPlans}
                crewDispatches={crewDispatches}
                onAlertClick={(alert) => {
                  console.log('Alert clicked:', alert.alert_id);
                }}
              />
            </Suspense>
          </TabsContent>

          <TabsContent value="packet-analysis">
            <Suspense fallback={<TabLoadingFallback />}>
              <PacketAnalysisView captureId={packetCaptureId} />
            </Suspense>
          </TabsContent>

          <TabsContent value="edge-ops">
            <Suspense fallback={<TabLoadingFallback />}>
              <EdgeOperationsView onOpenCapture={openCapture} />
            </Suspense>
          </TabsContent>

          <TabsContent value="architecture">
            <Suspense fallback={<TabLoadingFallback />}>
              <ArchitectureView nodes={nodes.length} metrics={archMetrics || undefined} />
            </Suspense>
          </TabsContent>

          <TabsContent value="config-management">
            <Suspense fallback={<TabLoadingFallback />}>
              <ConfigManagementView />
            </Suspense>
          </TabsContent>

        </Tabs>
      </main>

      <footer className="mt-auto border-t border-gray-600 bg-white">
        <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between text-xs text-gray-500">
          <span>© 2025 Cloudera, Inc. All rights reserved.</span>
          <img src="/cloudera-logo.png" alt="Cloudera" className="h-[18px] w-auto" />
        </div>
        <div className="h-2 bg-brand-orange" />
      </footer>

      {/* AI Settings Modal */}
      {showSettings && (
        <Suspense fallback={<TabLoadingFallback />}>
          <AISettingsPanel
            onClose={() => setShowSettings(false)}
            onRegenerateData={handleRegenerateAllData}
          />
        </Suspense>
      )}
    </div>
  );
};

export default Dashboard;
