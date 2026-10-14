import { useState, useEffect, useCallback } from 'react';
import { FiberNode } from '@/types';
import {
  getFiberNodes,
  loadFromBackend,
} from '@/services/memoryStore';
import { generateSensorDataBatch } from '@/services/sensorDataGenerator';
import {
  insertAntennaSensors,
  insertWeatherData,
  insertEnvSensors,
  insertEquipmentSensors,
} from '@/services/memoryStore';
import { llmService } from '@/services/llmService';
import { systemSettingsService } from '@/services/systemSettingsService';

interface UseBackendConnectionReturn {
  /** Whether backend setup screen should be shown */
  needsSetup: boolean;
  /** Whether the app is still loading/connecting */
  loading: boolean;
  /** Human-readable loading status message */
  loadingMessage: string;
  /** Error message if connection failed, null otherwise */
  error: string | null;
  /** Nodes loaded from backend */
  nodes: FiberNode[];
  /** Called when BackendSetup form completes successfully */
  handleBackendConfigured: () => void;
  /** Allows external code to set loading state (e.g., during regeneration) */
  setLoading: (loading: boolean) => void;
  /** Allows external code to set loading message */
  setLoadingMessage: (message: string) => void;
  /** Allows external code to set nodes (e.g., after regeneration) */
  setNodes: (nodes: FiberNode[]) => void;
  /** Allows external code to set error */
  setError: (error: string | null) => void;
  /** Allows external code to set needsSetup */
  setNeedsSetup: (needsSetup: boolean) => void;
}

/**
 * Manages backend connection initialization, retry logic, and initial data loading.
 *
 * On mount (if backend URL is configured), it:
 * 1. Loads system settings
 * 2. Retries connecting to backend up to 30 times (1s apart)
 * 3. Loads nodes from backend
 * 4. Initializes LLM service
 * 5. Defers sensor data generation until after first render
 */
export function useBackendConnection(): UseBackendConnectionReturn {
  const [needsSetup, setNeedsSetup] = useState(() => !systemSettingsService.isBackendConfigured());
  const [loading, setLoading] = useState(true);
  const [loadingMessage, setLoadingMessage] = useState('Initializing...');
  const [error, setError] = useState<string | null>(null);
  const [nodes, setNodes] = useState<FiberNode[]>([]);

  const handleBackendConfigured = useCallback(() => {
    setNeedsSetup(false);
    setLoading(true);
    setLoadingMessage('Connecting to backend...');
  }, []);

  // Main initialization effect
  useEffect(() => {
    if (needsSetup) {
      setLoading(false);
      return;
    }

    const initialize = async () => {
      try {
        // Load system settings first (determines backend URL)
        setLoadingMessage('Loading system settings...');
        await systemSettingsService.loadSettings();

        // Connect to backend - retry with fast initial attempts
        let backendLoaded = false;
        let retryCount = 0;
        const maxRetries = 30;

        while (!backendLoaded && retryCount < maxRetries) {
          if (retryCount === 0) {
            setLoadingMessage('Connecting to backend...');
          } else {
            setLoadingMessage(`Connecting to backend... (attempt ${retryCount + 1})`);
          }

          backendLoaded = await loadFromBackend();

          if (!backendLoaded) {
            retryCount++;
            console.log(`Backend not available, retrying in 1 second... (attempt ${retryCount}/${maxRetries})`);
            await new Promise(resolve => setTimeout(resolve, 1000));
          }
        }

        if (!backendLoaded) {
          throw new Error('Unable to connect to backend after multiple attempts. Please ensure the backend server is running.');
        }

        console.log('Using backend data source');
        setLoadingMessage('Loading data from backend...');
        const currentNodes = await getFiberNodes();
        console.log(`Loaded ${currentNodes.length} nodes from backend`);

        setNodes(currentNodes);

        // Initialize LLM service from backend
        try {
          const initialized = await llmService.initializeFromBackend();
          if (initialized) {
            console.log('LLM service initialized from backend');
          } else {
            console.log('LLM service not configured');
          }
        } catch (err) {
          console.error('Failed to initialize LLM service:', err);
        }

        setLoadingMessage('Starting real-time monitoring...');
        setLoading(false);
      } catch (err) {
        console.error('Initialization error:', err);
        setError('Failed to initialize application');
        setLoading(false);
      }
    };

    initialize();
  }, [needsSetup]);

  // Deferred sensor data generation - runs after initial render for faster startup
  useEffect(() => {
    if (loading || nodes.length === 0) return;

    const timeoutId = setTimeout(() => {
      console.log(`Generating sensor data for ${nodes.length} nodes (deferred)...`);
      const sensorBatch = generateSensorDataBatch(nodes, new Date());
      insertAntennaSensors(sensorBatch.antennaSensors);
      insertWeatherData(sensorBatch.weatherData);
      insertEnvSensors(sensorBatch.environmentalSensors);
      insertEquipmentSensors(sensorBatch.equipmentSensors);
      console.log('Sensor data generation complete');
    }, 100);

    return () => clearTimeout(timeoutId);
  }, [loading, nodes.length]);

  return {
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
  };
}
