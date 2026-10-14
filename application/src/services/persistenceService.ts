/**
 * IndexedDB persistence service for storing network data across sessions
 * Enhanced with sensor data persistence
 */

import {
  FiberNode,
  KPIMetrics,
  Alert,
  SelfHealingAction,
  AntennaSensorData,
  WeatherData,
  EnvironmentalSensor,
  EquipmentSensorData,
} from '@/types';

const DB_NAME = 'TelcoNetworkDB';
const DB_VERSION = 2; // Incremented for new sensor stores
const STORES = {
  NODES: 'nodes',
  KPI_METRICS: 'kpi_metrics',
  ALERTS: 'alerts',
  ACTIONS: 'actions',
  ANTENNA_SENSORS: 'antenna_sensors',
  WEATHER_DATA: 'weather_data',
  ENV_SENSORS: 'env_sensors',
  EQUIPMENT_SENSORS: 'equipment_sensors',
};

let db: IDBDatabase | null = null;

/**
 * Initialize IndexedDB
 */
export const initPersistence = async (): Promise<void> => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      db = request.result;
      console.log('IndexedDB initialized for persistence');
      resolve();
    };

    request.onupgradeneeded = (event) => {
      const database = (event.target as IDBOpenDBRequest).result;

      // Create object stores if they don't exist
      if (!database.objectStoreNames.contains(STORES.NODES)) {
        database.createObjectStore(STORES.NODES, { keyPath: 'node_id' });
      }
      if (!database.objectStoreNames.contains(STORES.KPI_METRICS)) {
        const kpiStore = database.createObjectStore(STORES.KPI_METRICS, { keyPath: 'metric_id' });
        kpiStore.createIndex('timestamp', 'timestamp', { unique: false });
        kpiStore.createIndex('node_id', 'node_id', { unique: false });
      }
      if (!database.objectStoreNames.contains(STORES.ALERTS)) {
        database.createObjectStore(STORES.ALERTS, { keyPath: 'alert_id' });
      }
      if (!database.objectStoreNames.contains(STORES.ACTIONS)) {
        database.createObjectStore(STORES.ACTIONS, { keyPath: 'action_id' });
      }

      // Sensor data stores (v2)
      if (!database.objectStoreNames.contains(STORES.ANTENNA_SENSORS)) {
        const antennaStore = database.createObjectStore(STORES.ANTENNA_SENSORS, { keyPath: 'sensor_id' });
        antennaStore.createIndex('node_id', 'node_id', { unique: false });
        antennaStore.createIndex('timestamp', 'timestamp', { unique: false });
      }
      if (!database.objectStoreNames.contains(STORES.WEATHER_DATA)) {
        const weatherStore = database.createObjectStore(STORES.WEATHER_DATA, { keyPath: 'weather_id' });
        weatherStore.createIndex('node_id', 'node_id', { unique: false });
        weatherStore.createIndex('timestamp', 'timestamp', { unique: false });
      }
      if (!database.objectStoreNames.contains(STORES.ENV_SENSORS)) {
        const envStore = database.createObjectStore(STORES.ENV_SENSORS, { keyPath: 'sensor_id' });
        envStore.createIndex('node_id', 'node_id', { unique: false });
        envStore.createIndex('timestamp', 'timestamp', { unique: false });
      }
      if (!database.objectStoreNames.contains(STORES.EQUIPMENT_SENSORS)) {
        const equipStore = database.createObjectStore(STORES.EQUIPMENT_SENSORS, { keyPath: 'sensor_id' });
        equipStore.createIndex('node_id', 'node_id', { unique: false });
        equipStore.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
  });
};

/**
 * Save nodes to IndexedDB
 */
export const saveNodes = async (nodes: FiberNode[]): Promise<void> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.NODES], 'readwrite');
    const store = transaction.objectStore(STORES.NODES);

    // Clear existing data
    store.clear();

    // Add all nodes
    nodes.forEach(node => store.put(node));

    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

/**
 * Load nodes from IndexedDB
 */
export const loadNodes = async (): Promise<FiberNode[]> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.NODES], 'readonly');
    const store = transaction.objectStore(STORES.NODES);
    const request = store.getAll();

    request.onsuccess = () => {
      const nodes = request.result as FiberNode[];
      // Convert date strings back to Date objects
      nodes.forEach(node => {
        if (node.commissioned_date) node.commissioned_date = new Date(node.commissioned_date);
        if (node.last_maintenance) node.last_maintenance = new Date(node.last_maintenance);
      });
      resolve(nodes);
    };
    request.onerror = () => reject(request.error);
  });
};

/**
 * Save KPI metrics to IndexedDB (batch save with limit)
 */
export const saveKPIMetrics = async (metrics: KPIMetrics[], maxRecords: number = 100000): Promise<void> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.KPI_METRICS], 'readwrite');
    const store = transaction.objectStore(STORES.KPI_METRICS);

    // Get current count
    const countRequest = store.count();
    countRequest.onsuccess = () => {
      const currentCount = countRequest.result;

      // If we're over the limit, clear old data first
      if (currentCount > maxRecords) {
        const index = store.index('timestamp');
        const cursorRequest = index.openCursor();
        const deleteCount = Math.min(currentCount - maxRecords + metrics.length, currentCount);
        let deleted = 0;

        cursorRequest.onsuccess = (event) => {
          const cursor = (event.target as IDBRequest).result;
          if (cursor && deleted < deleteCount) {
            cursor.delete();
            deleted++;
            cursor.continue();
          }
        };
      }

      // Add new metrics
      metrics.forEach(metric => store.put(metric));

      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    };
  });
};

/**
 * Load recent KPI metrics from IndexedDB
 */
export const loadKPIMetrics = async (limit: number = 100000): Promise<KPIMetrics[]> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.KPI_METRICS], 'readonly');
    const store = transaction.objectStore(STORES.KPI_METRICS);
    const index = store.index('timestamp');
    const request = index.openCursor(null, 'prev'); // Start from most recent

    const metrics: KPIMetrics[] = [];
    request.onsuccess = (event) => {
      const cursor = (event.target as IDBRequest).result;
      if (cursor && metrics.length < limit) {
        const metric = cursor.value as KPIMetrics;
        // Convert timestamp back to Date
        metric.timestamp = new Date(metric.timestamp);
        metrics.push(metric);
        cursor.continue();
      } else {
        // Reverse to get chronological order
        resolve(metrics.reverse());
      }
    };
    request.onerror = () => reject(request.error);
  });
};

/**
 * Save alerts to IndexedDB
 */
export const saveAlerts = async (alerts: Alert[]): Promise<void> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.ALERTS], 'readwrite');
    const store = transaction.objectStore(STORES.ALERTS);

    alerts.forEach(alert => store.put(alert));

    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

/**
 * Load alerts from IndexedDB
 */
export const loadAlerts = async (): Promise<Alert[]> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.ALERTS], 'readonly');
    const store = transaction.objectStore(STORES.ALERTS);
    const request = store.getAll();

    request.onsuccess = () => {
      const alerts = request.result as Alert[];
      // Convert date strings back to Date objects
      alerts.forEach(alert => {
        alert.timestamp = new Date(alert.timestamp);
        if (alert.resolved_at) alert.resolved_at = new Date(alert.resolved_at);
      });
      resolve(alerts);
    };
    request.onerror = () => reject(request.error);
  });
};

/**
 * Save actions to IndexedDB
 */
export const saveActions = async (actions: SelfHealingAction[]): Promise<void> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.ACTIONS], 'readwrite');
    const store = transaction.objectStore(STORES.ACTIONS);

    actions.forEach(action => store.put(action));

    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

/**
 * Load actions from IndexedDB
 */
export const loadActions = async (): Promise<SelfHealingAction[]> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.ACTIONS], 'readonly');
    const store = transaction.objectStore(STORES.ACTIONS);
    const request = store.getAll();

    request.onsuccess = () => {
      const actions = request.result as SelfHealingAction[];
      // Convert date strings back to Date objects
      actions.forEach(action => {
        action.timestamp = new Date(action.timestamp);
        if (action.completion_time) action.completion_time = new Date(action.completion_time);
      });
      resolve(actions);
    };
    request.onerror = () => reject(request.error);
  });
};

/**
 * Save antenna sensor data to IndexedDB
 */
export const saveAntennaSensors = async (sensors: AntennaSensorData[]): Promise<void> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.ANTENNA_SENSORS], 'readwrite');
    const store = transaction.objectStore(STORES.ANTENNA_SENSORS);

    sensors.forEach(sensor => store.put(sensor));

    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

/**
 * Load antenna sensors for a specific node
 */
export const loadAntennaSensors = async (nodeId?: string): Promise<AntennaSensorData[]> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.ANTENNA_SENSORS], 'readonly');
    const store = transaction.objectStore(STORES.ANTENNA_SENSORS);

    let request;
    if (nodeId) {
      const index = store.index('node_id');
      request = index.getAll(nodeId);
    } else {
      request = store.getAll();
    }

    request.onsuccess = () => {
      const sensors = request.result as AntennaSensorData[];
      sensors.forEach(sensor => {
        sensor.timestamp = new Date(sensor.timestamp);
        sensor.last_calibration = new Date(sensor.last_calibration);
      });
      resolve(sensors);
    };
    request.onerror = () => reject(request.error);
  });
};

/**
 * Save weather data to IndexedDB
 */
export const saveWeatherData = async (weatherData: WeatherData[]): Promise<void> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.WEATHER_DATA], 'readwrite');
    const store = transaction.objectStore(STORES.WEATHER_DATA);

    weatherData.forEach(data => store.put(data));

    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

/**
 * Load weather data for a specific node
 */
export const loadWeatherData = async (nodeId?: string): Promise<WeatherData[]> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.WEATHER_DATA], 'readonly');
    const store = transaction.objectStore(STORES.WEATHER_DATA);

    let request;
    if (nodeId) {
      const index = store.index('node_id');
      request = index.getAll(nodeId);
    } else {
      request = store.getAll();
    }

    request.onsuccess = () => {
      const weatherData = request.result as WeatherData[];
      weatherData.forEach(data => {
        data.timestamp = new Date(data.timestamp);
      });
      resolve(weatherData);
    };
    request.onerror = () => reject(request.error);
  });
};

/**
 * Save environmental sensor data to IndexedDB
 */
export const saveEnvSensors = async (sensors: EnvironmentalSensor[]): Promise<void> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.ENV_SENSORS], 'readwrite');
    const store = transaction.objectStore(STORES.ENV_SENSORS);

    sensors.forEach(sensor => store.put(sensor));

    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

/**
 * Load environmental sensors for a specific node
 */
export const loadEnvSensors = async (nodeId?: string): Promise<EnvironmentalSensor[]> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.ENV_SENSORS], 'readonly');
    const store = transaction.objectStore(STORES.ENV_SENSORS);

    let request;
    if (nodeId) {
      const index = store.index('node_id');
      request = index.getAll(nodeId);
    } else {
      request = store.getAll();
    }

    request.onsuccess = () => {
      const sensors = request.result as EnvironmentalSensor[];
      sensors.forEach(sensor => {
        sensor.timestamp = new Date(sensor.timestamp);
      });
      resolve(sensors);
    };
    request.onerror = () => reject(request.error);
  });
};

/**
 * Save equipment sensor data to IndexedDB
 */
export const saveEquipmentSensors = async (sensors: EquipmentSensorData[]): Promise<void> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.EQUIPMENT_SENSORS], 'readwrite');
    const store = transaction.objectStore(STORES.EQUIPMENT_SENSORS);

    sensors.forEach(sensor => store.put(sensor));

    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

/**
 * Load equipment sensors for a specific node
 */
export const loadEquipmentSensors = async (nodeId?: string): Promise<EquipmentSensorData[]> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction([STORES.EQUIPMENT_SENSORS], 'readonly');
    const store = transaction.objectStore(STORES.EQUIPMENT_SENSORS);

    let request;
    if (nodeId) {
      const index = store.index('node_id');
      request = index.getAll(nodeId);
    } else {
      request = store.getAll();
    }

    request.onsuccess = () => {
      const sensors = request.result as EquipmentSensorData[];
      sensors.forEach(sensor => {
        sensor.timestamp = new Date(sensor.timestamp);
        sensor.last_reboot = new Date(sensor.last_reboot);
        sensor.component_health.forEach(comp => {
          comp.last_maintenance = new Date(comp.last_maintenance);
        });
      });
      resolve(sensors);
    };
    request.onerror = () => reject(request.error);
  });
};

/**
 * Clear all persisted data (useful for reset)
 */
export const clearAllData = async (): Promise<void> => {
  if (!db) await initPersistence();

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction(
      [
        STORES.NODES,
        STORES.KPI_METRICS,
        STORES.ALERTS,
        STORES.ACTIONS,
        STORES.ANTENNA_SENSORS,
        STORES.WEATHER_DATA,
        STORES.ENV_SENSORS,
        STORES.EQUIPMENT_SENSORS,
      ],
      'readwrite'
    );

    transaction.objectStore(STORES.NODES).clear();
    transaction.objectStore(STORES.KPI_METRICS).clear();
    transaction.objectStore(STORES.ALERTS).clear();
    transaction.objectStore(STORES.ACTIONS).clear();
    transaction.objectStore(STORES.ANTENNA_SENSORS).clear();
    transaction.objectStore(STORES.WEATHER_DATA).clear();
    transaction.objectStore(STORES.ENV_SENSORS).clear();
    transaction.objectStore(STORES.EQUIPMENT_SENSORS).clear();

    transaction.oncomplete = () => {
      console.log('All persisted data cleared');
      resolve();
    };
    transaction.onerror = () => reject(transaction.error);
  });
};
