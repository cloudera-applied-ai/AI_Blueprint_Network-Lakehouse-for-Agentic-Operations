/**
 * In-memory data store with IndexedDB persistence
 * Fast in-memory access with automatic persistence across sessions
 */

import {
  FiberNode,
  KPIMetrics,
  Alert,
  SelfHealingAction,
  NetworkHealthSummary,
  NodeStatus,
  AlertStatus,
  AntennaSensorData,
  WeatherData,
  EnvironmentalSensor,
  EquipmentSensorData,
} from '@/types';
import { DB_CONFIG, CACHE_CONFIG } from '@/constants';
import { getCachedData, invalidateCache } from '@/utils/helpers';
import {
  initPersistence,
  loadNodes as loadPersistedNodes,
  saveNodes as savePersistedNodes,
  loadKPIMetrics as loadPersistedKPIMetrics,
  saveKPIMetrics as savePersistedKPIMetrics,
  loadAlerts as loadPersistedAlerts,
  saveAlerts as savePersistedAlerts,
  loadActions as loadPersistedActions,
  saveActions as savePersistedActions,
  loadAntennaSensors as loadPersistedAntennaSensors,
  saveAntennaSensors as savePersistedAntennaSensors,
  loadWeatherData as loadPersistedWeatherData,
  saveWeatherData as savePersistedWeatherData,
  loadEnvSensors as loadPersistedEnvSensors,
  saveEnvSensors as savePersistedEnvSensors,
  loadEquipmentSensors as loadPersistedEquipmentSensors,
  saveEquipmentSensors as savePersistedEquipmentSensors,
} from './persistenceService';
import {
  getNodes,
  getKPIs,
  getAlerts,
  getActions,
  getAggregatedKPIs,
  checkBackendHealth as apiCheckBackendHealth,
  type AggregatedKPIsResponse,
} from './apiClient';
import { initializeRemediationSteps, syncRemediationProgress } from './remediationSteps';

/**
 * Parse a timestamp from the backend as UTC.
 * Python's datetime.now().isoformat() produces "2026-04-04T18:16:36.123456"
 * without a timezone suffix.  JavaScript's Date constructor treats that as
 * LOCAL time, which breaks elapsed-time calculations when the browser isn't
 * in UTC.  Appending "Z" forces UTC interpretation.
 */
function parseUTC(ts: string | Date | undefined | null): Date {
  if (!ts) return new Date();
  if (ts instanceof Date) return ts;
  // Already has timezone info → parse as-is
  if (ts.endsWith('Z') || ts.includes('+') || /T\d{2}:\d{2}:\d{2}.*-\d{2}/.test(ts)) {
    return new Date(ts);
  }
  return new Date(ts + 'Z');
}

// In-memory storage with persistence
class MemoryStore {
  private nodes: Map<string, FiberNode> = new Map();
  private kpiMetrics: KPIMetrics[] = [];
  private kpiByNode: Map<string, KPIMetrics[]> = new Map(); // O(1) node lookup index
  private alerts: Map<string, Alert> = new Map();
  private actions: Map<string, SelfHealingAction> = new Map();

  // Sensor data caches (keyed by node_id for fast lookup)
  private antennaSensors: Map<string, AntennaSensorData> = new Map();
  private weatherData: Map<string, WeatherData> = new Map();
  private envSensors: Map<string, EnvironmentalSensor> = new Map();
  private equipmentSensors: Map<string, EquipmentSensorData> = new Map();

  // Memoization cache for expensive computations
  private healthSummaryCache: { data: NetworkHealthSummary; timestamp: number } | null = null;
  private static readonly HEALTH_CACHE_TTL = 30000; // Increased to 30 seconds for better performance

  // Cached sorted lists for frequent queries
  private cachedActiveAlerts: Alert[] | null = null;
  private cachedActiveAlertsTime: number = 0;
  private static readonly ALERT_CACHE_TTL = 1000; // 1 second cache for active alerts

  private persistenceEnabled = true;
  private autoSaveInterval: NodeJS.Timeout | null = null;
  private dataLoaded = false;
  private sensorDataLoaded = false;
  private backendEnabled = false;
  private backendHealthy = false;

  // Insert operations
  insertNodes(nodes: FiberNode[]): void {
    nodes.forEach((node) => {
      this.nodes.set(node.node_id, node);
    });
  }

  insertKPIMetrics(metrics: KPIMetrics[]): void {
    // Handle large arrays by batching to avoid "too many arguments" error
    const BATCH_SIZE = 50000; // Safe batch size for push operations

    if (metrics.length > BATCH_SIZE) {
      console.log(`Inserting ${metrics.length.toLocaleString()} KPI records in batches...`);
      for (let i = 0; i < metrics.length; i += BATCH_SIZE) {
        const batch = metrics.slice(i, i + BATCH_SIZE);
        this.kpiMetrics.push(...batch);
        // Update node index for each batch
        this.updateKPINodeIndex(batch);

        if ((i + BATCH_SIZE) % 500000 === 0 || i + BATCH_SIZE >= metrics.length) {
          const progress = Math.min(100, ((i + BATCH_SIZE) / metrics.length * 100)).toFixed(1);
          console.log(`Insertion progress: ${progress}% (${Math.min(i + BATCH_SIZE, metrics.length).toLocaleString()} records)`);
        }
      }
      console.log(`Insertion complete: ${metrics.length.toLocaleString()} total records`);
    } else {
      this.kpiMetrics.push(...metrics);
      // Update node index
      this.updateKPINodeIndex(metrics);
    }

    this.cleanupOldData();
  }

  // Maintain O(1) node lookup index for KPIs
  private updateKPINodeIndex(metrics: KPIMetrics[]): void {
    for (const kpi of metrics) {
      const existing = this.kpiByNode.get(kpi.node_id) || [];
      existing.push(kpi);
      this.kpiByNode.set(kpi.node_id, existing);
    }
  }

  // Rebuild the entire KPI node index (called after bulk operations like cleanup)
  rebuildKPINodeIndex(): void {
    this.kpiByNode.clear();
    for (const kpi of this.kpiMetrics) {
      const existing = this.kpiByNode.get(kpi.node_id) || [];
      existing.push(kpi);
      this.kpiByNode.set(kpi.node_id, existing);
    }
  }

  insertAlerts(alerts: Alert[]): void {
    alerts.forEach((alert) => {
      this.alerts.set(alert.alert_id, alert);
    });
    // Invalidate cached active alerts list
    this.cachedActiveAlerts = null;
  }

  insertActions(actions: SelfHealingAction[]): void {
    actions.forEach((action) => {
      this.actions.set(action.action_id, action);
    });
  }

  // Query operations
  getAllNodes(): FiberNode[] {
    return Array.from(this.nodes.values());
  }

  getNodeById(nodeId: string): FiberNode | undefined {
    return this.nodes.get(nodeId);
  }

  updateNodeStatus(nodeId: string, status: NodeStatus): void {
    const node = this.nodes.get(nodeId);
    if (node) {
      node.status = status;
      this.nodes.set(nodeId, node);
    }
  }

  getActiveAlerts(): Alert[] {
    const now = Date.now();
    // Return cached result if still valid
    if (this.cachedActiveAlerts && now - this.cachedActiveAlertsTime < MemoryStore.ALERT_CACHE_TTL) {
      return this.cachedActiveAlerts;
    }

    // Rebuild cache
    this.cachedActiveAlerts = Array.from(this.alerts.values())
      .filter((alert) => alert.status === AlertStatus.ACTIVE)
      .sort((a, b) => {
        // Sort by severity (critical first) then by timestamp (newest first)
        const severityOrder: Record<string, number> = { critical: 0, warning: 1, info: 2 };
        const severityDiff = (severityOrder[a.severity] ?? 3) - (severityOrder[b.severity] ?? 3);
        if (severityDiff !== 0) return severityDiff;
        return b.timestamp.getTime() - a.timestamp.getTime();
      })
      .slice(0, 100);
    this.cachedActiveAlertsTime = now;

    return this.cachedActiveAlerts;
  }

  getRecentActions(limit: number = 50): SelfHealingAction[] {
    return Array.from(this.actions.values())
      .filter((action) => action.timestamp) // Filter out actions without timestamps
      .sort((a, b) => {
        const aTime = typeof a.timestamp === 'string' ? new Date(a.timestamp).getTime() : a.timestamp.getTime();
        const bTime = typeof b.timestamp === 'string' ? new Date(b.timestamp).getTime() : b.timestamp.getTime();
        return bTime - aTime;
      })
      .slice(0, limit);
  }

  // Get all actions without limit - useful for dashboards that need full status breakdown
  getAllActions(): SelfHealingAction[] {
    return Array.from(this.actions.values())
      .filter((action) => action.timestamp);
  }

  getAlertsByNode(nodeId: string): Alert[] {
    return Array.from(this.alerts.values())
      .filter((alert) => alert.node_id === nodeId)
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }

  getActionsByNode(nodeId: string): SelfHealingAction[] {
    return Array.from(this.actions.values())
      .filter((action) => action.node_id === nodeId)
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }

  getKPIMetricsForNode(nodeId: string, limit: number = 1000): KPIMetrics[] {
    // Use indexed lookup for O(1) access instead of O(n) filter
    const nodeMetrics = this.kpiByNode.get(nodeId) || [];
    return nodeMetrics
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
      .slice(-limit);
  }

  getRecentKPIMetrics(limit: number = 100): KPIMetrics[] {
    // Get KPIs from the last 5 minutes instead of just last N records
    // This ensures we get a time range of data for proper chart rendering
    const now = Date.now();
    const fiveMinutesAgo = new Date(now - 5 * 60 * 1000);

    const recentMetrics = this.kpiMetrics.filter(
      (kpi) => kpi.timestamp >= fiveMinutesAgo
    );

    // If we don't have enough recent data yet (e.g., just started),
    // fall back to last N records
    if (recentMetrics.length < 10) {
      return this.kpiMetrics
        .slice(-limit)
        .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
    }

    // Return recent data, limited to avoid performance issues
    return recentMetrics
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
      .slice(-limit);
  }

  /**
   * Get KPI metrics for a specific time range (e.g., last 30 days)
   * Returns aggregated data suitable for charting
   */
  getKPIMetricsForTimeRange(days: number = 30): KPIMetrics[] {
    const now = Date.now();
    const startTime = new Date(now - days * 24 * 60 * 60 * 1000);

    return this.kpiMetrics
      .filter((kpi) => kpi.timestamp >= startTime)
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }

  /**
   * Get daily aggregated KPI data for charting (last N days)
   * Returns one data point per day per node for efficient charting
   */
  getDailyAggregatedKPIs(days: number = 30): {
    date: string;
    avgDsSnr: number;
    avgPacketLoss: number;
    avgUsSnr: number;
    avgThroughputDl: number;
    avgLatency: number;
    totalActiveModems: number;
    nodeCount: number;
  }[] {
    const now = Date.now();
    const startTime = new Date(now - days * 24 * 60 * 60 * 1000);

    // Filter to time range
    const metricsInRange = this.kpiMetrics.filter((kpi) => kpi.timestamp >= startTime);

    // Group by date
    const dailyData = new Map<string, {
      dsSnrSum: number;
      packetLossSum: number;
      usSnrSum: number;
      throughputSum: number;
      latencySum: number;
      activeModemsSum: number;
      count: number;
      nodes: Set<string>;
    }>();

    metricsInRange.forEach((kpi) => {
      const dateKey = kpi.timestamp.toISOString().split('T')[0];
      if (!dailyData.has(dateKey)) {
        dailyData.set(dateKey, {
          dsSnrSum: 0,
          packetLossSum: 0,
          usSnrSum: 0,
          throughputSum: 0,
          latencySum: 0,
          activeModemsSum: 0,
          count: 0,
          nodes: new Set(),
        });
      }
      const day = dailyData.get(dateKey)!;
      day.dsSnrSum += kpi.ds_snr_db;
      day.packetLossSum += kpi.packet_loss_percent;
      day.usSnrSum += kpi.us_snr_db;
      day.throughputSum += kpi.downstream_throughput_mbps;
      day.latencySum += kpi.latency_ms;
      day.activeModemsSum += kpi.active_modems;
      day.count++;
      day.nodes.add(kpi.node_id);
    });

    // Convert to array sorted by date
    return Array.from(dailyData.entries())
      .map(([date, data]) => ({
        date,
        avgDsSnr: data.dsSnrSum / data.count,
        avgPacketLoss: data.packetLossSum / data.count,
        avgUsSnr: data.usSnrSum / data.count,
        avgThroughputDl: data.throughputSum / data.count,
        avgLatency: data.latencySum / data.count,
        totalActiveModems: Math.round(data.activeModemsSum / data.count),
        nodeCount: data.nodes.size,
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }

  /**
   * Get alerts grouped by day for the last N days (for charting)
   */
  getAlertsForTimeRange(days: number = 30): {
    date: string;
    critical: number;
    warning: number;
    info: number;
    total: number;
  }[] {
    const now = Date.now();
    const startTime = new Date(now - days * 24 * 60 * 60 * 1000);

    const alertsInRange = Array.from(this.alerts.values())
      .filter((alert) => alert.timestamp >= startTime);

    // Group by date
    const dailyAlerts = new Map<string, { critical: number; warning: number; info: number }>();

    alertsInRange.forEach((alert) => {
      const dateKey = alert.timestamp.toISOString().split('T')[0];
      if (!dailyAlerts.has(dateKey)) {
        dailyAlerts.set(dateKey, { critical: 0, warning: 0, info: 0 });
      }
      const day = dailyAlerts.get(dateKey)!;
      if (alert.severity === 'critical') day.critical++;
      else if (alert.severity === 'warning') day.warning++;
      else day.info++;
    });

    return Array.from(dailyAlerts.entries())
      .map(([date, data]) => ({
        date,
        ...data,
        total: data.critical + data.warning + data.info,
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }

  /**
   * Get actions grouped by day for the last N days (for charting)
   */
  getActionsForTimeRange(days: number = 30): {
    date: string;
    completed: number;
    failed: number;
    pending: number;
    inProgress: number;
    total: number;
    avgEffectiveness: number;
  }[] {
    const now = Date.now();
    const startTime = new Date(now - days * 24 * 60 * 60 * 1000);

    const actionsInRange = Array.from(this.actions.values())
      .filter((action) => action.timestamp >= startTime);

    // Group by date
    const dailyActions = new Map<string, {
      completed: number;
      failed: number;
      pending: number;
      inProgress: number;
      effectivenessSum: number;
      effectivenessCount: number;
    }>();

    actionsInRange.forEach((action) => {
      const dateKey = action.timestamp.toISOString().split('T')[0];
      if (!dailyActions.has(dateKey)) {
        dailyActions.set(dateKey, {
          completed: 0, failed: 0, pending: 0, inProgress: 0,
          effectivenessSum: 0, effectivenessCount: 0,
        });
      }
      const day = dailyActions.get(dateKey)!;
      if (action.status === 'completed') day.completed++;
      else if (action.status === 'failed') day.failed++;
      else if (action.status === 'pending') day.pending++;
      else if (action.status === 'in_progress') day.inProgress++;

      if (action.effectiveness_score) {
        day.effectivenessSum += action.effectiveness_score;
        day.effectivenessCount++;
      }
    });

    return Array.from(dailyActions.entries())
      .map(([date, data]) => ({
        date,
        completed: data.completed,
        failed: data.failed,
        pending: data.pending,
        inProgress: data.inProgress,
        total: data.completed + data.failed + data.pending + data.inProgress,
        avgEffectiveness: data.effectivenessCount > 0
          ? data.effectivenessSum / data.effectivenessCount
          : 0,
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }

  getNetworkHealthSummary(): NetworkHealthSummary {
    // Return cached value if still valid (within TTL)
    const now = Date.now();
    if (this.healthSummaryCache && now - this.healthSummaryCache.timestamp < MemoryStore.HEALTH_CACHE_TTL) {
      return this.healthSummaryCache.data;
    }

    const nodes = this.getAllNodes();
    const alerts = Array.from(this.alerts.values());
    const actions = Array.from(this.actions.values());

    // Count node statuses
    const statusCounts = nodes.reduce(
      (acc, n) => {
        acc[n.status] = (acc[n.status] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );

    // Count alert severities (only active)
    const activeAlerts = alerts.filter((a) => a.status === AlertStatus.ACTIVE);
    const alertCounts = activeAlerts.reduce(
      (acc, alert) => {
        acc[alert.severity] = (acc[alert.severity] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );

    // Count recent actions (last hour)
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
    const recentActions = actions.filter((a) => a.timestamp >= oneHourAgo);

    // Calculate average DS SNR and total active modems from recent KPIs
    const recentKPIs = this.kpiMetrics.slice(-100);
    const avgDsSnrDb =
      recentKPIs.length > 0
        ? recentKPIs.reduce((sum, kpi) => sum + kpi.ds_snr_db, 0) /
          recentKPIs.length
        : 0;

    // Calculate total active modems from most recent KPI per node
    const latestKPIsByNode = new Map<string, KPIMetrics>();
    this.kpiMetrics.slice(-nodes.length * 2).forEach(kpi => {
      const existing = latestKPIsByNode.get(kpi.node_id);
      if (!existing || kpi.timestamp > existing.timestamp) {
        latestKPIsByNode.set(kpi.node_id, kpi);
      }
    });
    const totalActiveModems = Array.from(latestKPIsByNode.values())
      .reduce((sum, kpi) => sum + kpi.active_modems, 0);

    const summary: NetworkHealthSummary = {
      total_nodes: nodes.length,
      healthy_nodes: statusCounts[NodeStatus.HEALTHY] || 0,
      degraded_nodes: statusCounts[NodeStatus.DEGRADED] || 0,
      outage_nodes: statusCounts[NodeStatus.OUTAGE] || 0,
      maintenance_nodes: statusCounts[NodeStatus.MAINTENANCE] || 0,
      active_alerts: activeAlerts.length,
      critical_alerts: alertCounts['critical'] || 0,
      warning_alerts: alertCounts['warning'] || 0,
      info_alerts: alertCounts['info'] || 0,
      self_healing_actions_last_hour: recentActions.length,
      network_availability:
        nodes.length > 0
          ? ((statusCounts[NodeStatus.HEALTHY] || 0) / nodes.length) * 100
          : 0,
      avg_ds_snr_db: avgDsSnrDb,
      total_active_modems: totalActiveModems,
      last_updated: new Date(),
    };

    // Cache the result
    this.healthSummaryCache = { data: summary, timestamp: Date.now() };

    return summary;
  }

  // Cleanup old data to prevent memory bloat
  // More aggressive cleanup to prevent RAM issues
  private cleanupOldData(): void {
    const cutoffTime = new Date(Date.now() - DB_CONFIG.RETENTION_DAYS * 24 * 60 * 60 * 1000);

    // Keep only KPI metrics within the retention window AND under max records
    const beforeCleanup = this.kpiMetrics.length;

    // If we're over 80% of max, be more aggressive
    const targetMax = this.kpiMetrics.length > DB_CONFIG.MAX_RECORDS * 0.8
      ? Math.floor(DB_CONFIG.MAX_RECORDS * 0.6) // Drop to 60% when near limit
      : DB_CONFIG.MAX_RECORDS;

    this.kpiMetrics = this.kpiMetrics
      .filter((kpi) => kpi.timestamp >= cutoffTime)
      .slice(-targetMax);

    const afterCleanup = this.kpiMetrics.length;
    if (beforeCleanup !== afterCleanup) {
      console.log(`KPI cleanup: removed ${beforeCleanup - afterCleanup} old records (keeping ${afterCleanup})`);
      // Rebuild index only when data changed significantly
      if (beforeCleanup - afterCleanup > 100) {
        this.rebuildKPINodeIndex();
      }
    }

    // Clean up resolved alerts older than 24 hours (more aggressive)
    const alertCutoff = new Date(Date.now() - 24 * 60 * 60 * 1000);
    let alertsRemoved = 0;
    Array.from(this.alerts.values()).forEach((alert) => {
      if (
        alert.status !== AlertStatus.ACTIVE &&
        alert.timestamp < alertCutoff
      ) {
        this.alerts.delete(alert.alert_id);
        alertsRemoved++;
      }
    });
    if (alertsRemoved > 0) {
      console.log(`Alert cleanup: removed ${alertsRemoved} old resolved alerts`);
    }

    // Clean up old completed actions (older than 24 hours)
    const actionCutoff = new Date(Date.now() - 24 * 60 * 60 * 1000);
    let actionsRemoved = 0;
    Array.from(this.actions.values()).forEach((action) => {
      if (action.completion_time && action.completion_time < actionCutoff) {
        this.actions.delete(action.action_id);
        actionsRemoved++;
      }
    });
    if (actionsRemoved > 0) {
      console.log(`Action cleanup: removed ${actionsRemoved} old completed actions`);
    }

    // Limit alerts and actions maps - use config values, keep minimal in memory
    const maxAlerts = DB_CONFIG.MAX_ALERTS || 200;
    const maxActions = DB_CONFIG.MAX_ACTIONS || 200;

    if (this.alerts.size > maxAlerts) {
      const sortedAlerts = Array.from(this.alerts.values())
        .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
        .slice(0, Math.floor(maxAlerts * 0.8)); // Keep 80% of max
      this.alerts.clear();
      sortedAlerts.forEach(a => this.alerts.set(a.alert_id, a));
      console.log(`Alert map trimmed to ${this.alerts.size} entries (max: ${maxAlerts})`);
    }

    if (this.actions.size > maxActions) {
      const sortedActions = Array.from(this.actions.values())
        .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
        .slice(0, Math.floor(maxActions * 0.8)); // Keep 80% of max
      this.actions.clear();
      sortedActions.forEach(a => this.actions.set(a.action_id, a));
      console.log(`Action map trimmed to ${this.actions.size} entries (max: ${maxActions})`);
    }
  }

  // Sensor data insert operations
  insertAntennaSensors(sensors: AntennaSensorData[]): void {
    sensors.forEach((sensor) => {
      this.antennaSensors.set(sensor.node_id, sensor); // One per node
    });
  }

  insertWeatherData(weatherData: WeatherData[]): void {
    weatherData.forEach((data) => {
      this.weatherData.set(data.node_id, data); // One per node
    });
  }

  insertEnvSensors(sensors: EnvironmentalSensor[]): void {
    sensors.forEach((sensor) => {
      this.envSensors.set(sensor.node_id, sensor); // One per node
    });
  }

  insertEquipmentSensors(sensors: EquipmentSensorData[]): void {
    sensors.forEach((sensor) => {
      this.equipmentSensors.set(sensor.node_id, sensor); // One per node
    });
  }

  // Sensor data query operations
  getAntennaSensor(nodeId: string): AntennaSensorData | undefined {
    return this.antennaSensors.get(nodeId);
  }

  getWeatherData(nodeId: string): WeatherData | undefined {
    return this.weatherData.get(nodeId);
  }

  getEnvSensor(nodeId: string): EnvironmentalSensor | undefined {
    return this.envSensors.get(nodeId);
  }

  getEquipmentSensor(nodeId: string): EquipmentSensorData | undefined {
    return this.equipmentSensors.get(nodeId);
  }

  getAllSensorData(nodeId: string) {
    return {
      antenna: this.antennaSensors.get(nodeId),
      weather: this.weatherData.get(nodeId),
      environmental: this.envSensors.get(nodeId),
      equipment: this.equipmentSensors.get(nodeId),
    };
  }

  // Get all equipment sensor data across all nodes for analysis
  getAllEquipmentSensors(): EquipmentSensorData[] {
    return Array.from(this.equipmentSensors.values());
  }

  // Get all antenna sensor data across all nodes for analysis
  getAllAntennaSensors(): AntennaSensorData[] {
    return Array.from(this.antennaSensors.values());
  }

  // Get all environmental sensor data across all nodes for analysis
  getAllEnvironmentalSensors(): EnvironmentalSensor[] {
    return Array.from(this.envSensors.values());
  }

  // Get all weather data across all nodes for analysis
  getAllWeatherData(): WeatherData[] {
    return Array.from(this.weatherData.values());
  }

  isSensorDataLoaded(): boolean {
    return this.sensorDataLoaded;
  }

  // Clear all data (for testing)
  clear(): void {
    this.nodes.clear();
    this.kpiMetrics = [];
    this.alerts.clear();
    this.actions.clear();
    this.antennaSensors.clear();
    this.weatherData.clear();
    this.envSensors.clear();
    this.equipmentSensors.clear();
  }

  // Persistence methods
  async loadFromPersistence(): Promise<boolean> {
    if (!this.persistenceEnabled || this.dataLoaded) return false;

    try {
      await initPersistence();

      const [
        persistedNodes,
        persistedKPIs,
        persistedAlerts,
        persistedActions,
        persistedAntenna,
        persistedWeather,
        persistedEnv,
        persistedEquipment,
      ] = await Promise.all([
        loadPersistedNodes(),
        loadPersistedKPIMetrics(DB_CONFIG.INDEXEDDB_MAX_RECORDS || 2000), // Load from IndexedDB (limited)
        loadPersistedAlerts(),
        loadPersistedActions(),
        loadPersistedAntennaSensors(),
        loadPersistedWeatherData(),
        loadPersistedEnvSensors(),
        loadPersistedEquipmentSensors(),
      ]);

      if (persistedNodes.length > 0) {
        console.log(`Loaded ${persistedNodes.length} nodes from persistence`);
        this.nodes = new Map(persistedNodes.map(t => [t.node_id, t]));
      }

      if (persistedKPIs.length > 0) {
        console.log(`Loaded ${persistedKPIs.length} KPI metrics from persistence`);
        this.kpiMetrics = persistedKPIs;
      }

      if (persistedAlerts.length > 0) {
        console.log(`Loaded ${persistedAlerts.length} alerts from persistence`);
        this.alerts = new Map(persistedAlerts.map(a => [a.alert_id, a]));
      }

      if (persistedActions.length > 0) {
        console.log(`Loaded ${persistedActions.length} actions from persistence`);
        this.actions = new Map(persistedActions.map(a => [a.action_id, a]));
      }

      // Load sensor data
      if (persistedAntenna.length > 0) {
        console.log(`Loaded ${persistedAntenna.length} antenna sensors from persistence`);
        this.antennaSensors = new Map(persistedAntenna.map(s => [s.node_id, s]));
      }

      if (persistedWeather.length > 0) {
        console.log(`Loaded ${persistedWeather.length} weather data records from persistence`);
        this.weatherData = new Map(persistedWeather.map(w => [w.node_id, w]));
      }

      if (persistedEnv.length > 0) {
        console.log(`Loaded ${persistedEnv.length} environmental sensors from persistence`);
        this.envSensors = new Map(persistedEnv.map(e => [e.node_id, e]));
      }

      if (persistedEquipment.length > 0) {
        console.log(`Loaded ${persistedEquipment.length} equipment sensors from persistence`);
        this.equipmentSensors = new Map(persistedEquipment.map(e => [e.node_id, e]));
      }

      this.dataLoaded = true;
      this.sensorDataLoaded = persistedAntenna.length > 0 || persistedWeather.length > 0;
      return true;
    } catch (error) {
      console.error('Failed to load persisted data:', error);
      return false;
    }
  }

  // Backend API methods
  async checkBackendHealth(): Promise<boolean> {
    try {
      this.backendHealthy = await apiCheckBackendHealth();
      return this.backendHealthy;
    } catch (error) {
      console.error('Backend health check failed:', error);
      this.backendHealthy = false;
      return false;
    }
  }

  async loadFromBackend(): Promise<boolean> {
    try {
      console.log('🔌 Attempting to load data from backend...');

      // Check backend health first
      const isHealthy = await this.checkBackendHealth();
      if (!isHealthy) {
        console.log('⚠️ Backend is not available');
        return false;
      }

      console.log('✅ Backend is healthy, fetching data...');

      // Calculate date range for initial data (1 day back for fast startup)
      // User can expand to larger time ranges on-demand via UI
      const oneDayAgo = new Date();
      oneDayAgo.setDate(oneDayAgo.getDate() - 1);
      const startTime = oneDayAgo.toISOString();

      // Fetch initial data from backend in parallel
      // - Nodes: Essential for UI (load all, max 5000)
      // - KPIs: Limited to reduce memory usage on startup
      // - Alerts/Actions: Recent data for monitoring
      const [nodesResponse, kpisResponse, alertsResponse, actionsResponse] = await Promise.all([
        getNodes({ limit: 8000 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 0 })),
        getKPIs({ limit: 500, start_time: startTime }).catch(() => ({ items: [], total: 0, page: 1, page_size: 0 })), // Reduced from 1000
        getAlerts({ limit: 300, start_time: startTime }).catch(() => ({ items: [], total: 0, page: 1, page_size: 0 })), // Reduced from 1000
        getActions({ limit: 200 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 0 })), // Reduced from 500
      ]);

      // Load nodes - normalize status to lowercase (backend returns uppercase)
      // Also add default values for geographic_region and provider for backward compatibility
      if (nodesResponse.items.length > 0) {
        console.log(`📡 Loaded ${nodesResponse.items.length} nodes from backend`);
        const normalizedNodes = nodesResponse.items.map((n: FiberNode) => ({
          ...n,
          status: (n.status?.toLowerCase() || 'healthy') as FiberNode['status'],
        }));
        this.insertNodes(normalizedNodes);
      }

      // Load KPIs - map backend fields to frontend interface
      if (kpisResponse.items.length > 0) {
        console.log(`📊 Loaded ${kpisResponse.items.length} KPI metrics from backend`);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const normalizedKPIs = kpisResponse.items.map((kpi: any) => ({
          metric_id: kpi.metric_id,
          node_id: kpi.node_id,
          timestamp: new Date(kpi.timestamp),
          // RF Signal Levels
          ds_power_level_dbmv: kpi.ds_power_level_dbmv || 0,
          us_power_level_dbmv: kpi.us_power_level_dbmv || 0,
          ds_snr_db: kpi.ds_snr_db || 0,
          us_snr_db: kpi.us_snr_db || 0,
          ds_mer_db: kpi.ds_mer_db || 0,
          us_mer_db: kpi.us_mer_db || 0,
          // Forward Error Correction
          fec_corrected_codewords: kpi.fec_corrected_codewords || 0,
          fec_uncorrected_codewords: kpi.fec_uncorrected_codewords || 0,
          // DOCSIS Timeouts
          t3_timeouts: kpi.t3_timeouts || 0,
          t4_timeouts: kpi.t4_timeouts || 0,
          // Throughput
          downstream_throughput_mbps: kpi.downstream_throughput_mbps || kpi.throughput_mbps || 0,
          upstream_throughput_mbps: kpi.upstream_throughput_mbps || (kpi.throughput_mbps ? kpi.throughput_mbps * 0.3 : 0),
          // Network Performance
          latency_ms: kpi.latency_ms || 0,
          packet_loss_percent: kpi.packet_loss_percent || 0,
          jitter_ms: kpi.jitter_ms || 0,
          // Channel Utilization
          ds_channel_utilization_percent: kpi.ds_channel_utilization_percent || 0,
          us_channel_utilization_percent: kpi.us_channel_utilization_percent || 0,
          ofdm_utilization_percent: kpi.ofdm_utilization_percent || 0,
          // Modem Counts
          active_modems: kpi.active_modems || 0,
          registered_modems: kpi.registered_modems || 0,
          offline_modems: kpi.offline_modems || 0,
          modems_with_flaps: kpi.modems_with_flaps || 0,
          // Equipment Health
          node_temperature: kpi.node_temperature || 0,
          node_cpu_utilization: kpi.node_cpu_utilization || 0,
          node_memory_utilization: kpi.node_memory_utilization || 0,
          power_supply_voltage: kpi.power_supply_voltage || 0,
        })) as KPIMetrics[];
        this.insertKPIMetrics(normalizedKPIs);
      }

      // Load alerts - map backend fields to frontend interface and normalize to lowercase
      if (alertsResponse.items.length > 0) {
        console.log(`⚠️ Loaded ${alertsResponse.items.length} alerts from backend`);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const normalizedAlerts = alertsResponse.items.map((alert: any) => ({
          alert_id: alert.alert_id,
          node_id: alert.node_id,
          timestamp: new Date(alert.timestamp),
          // Backend uses 'type', frontend uses 'alert_type'
          alert_type: (alert.type?.toLowerCase() || alert.alert_type?.toLowerCase() || 'node_outage') as Alert['alert_type'],
          severity: (alert.severity?.toLowerCase() || 'warning') as Alert['severity'],
          description: alert.description || alert.title || '',
          affected_kpis: alert.affected_kpis || [],
          ai_confidence: alert.ai_confidence || 0.8,
          model_name: alert.model_name || 'backend-generated',
          root_cause: alert.root_cause,
          status: (alert.status?.toLowerCase() || 'active') as Alert['status'],
          acknowledged_by: alert.acknowledged_by,
          resolved_at: alert.resolved_at ? new Date(alert.resolved_at) : undefined
        })) as Alert[];
        this.insertAlerts(normalizedAlerts);
      }

      // Load actions - map backend fields to frontend interface and normalize to lowercase
      if (actionsResponse.items.length > 0) {
        console.log(`🔧 Loading ${actionsResponse.items.length} self-healing actions from backend`);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const normalizedActions = actionsResponse.items.map((action: any) => {
          const normalizedAction: SelfHealingAction = {
            action_id: action.action_id,
            alert_id: action.alert_id || '',
            node_id: action.node_id,
            // Backend uses 'start_time', frontend uses 'timestamp'
            timestamp: parseUTC(action.start_time || action.timestamp),
            action_type: (action.action_type?.toLowerCase() || 'load_balance') as SelfHealingAction['action_type'],
            action_details: action.action_details || { description: action.description },
            status: (action.status?.toLowerCase() || 'pending') as SelfHealingAction['status'],
            effectiveness_score: action.effectiveness_score,
            // Backend uses 'end_time', frontend uses 'completion_time'
            completion_time: action.end_time ? parseUTC(action.end_time) : undefined,
            rollback_available: action.rollback_available ?? false,
            automated: action.automated ?? true
          };
          // Initialize remediation steps for workflow tracking
          initializeRemediationSteps(normalizedAction);
          // Sync step progress based on action status and elapsed time
          syncRemediationProgress(normalizedAction);
          return normalizedAction;
        });
        this.insertActions(normalizedActions);

        // Debug: count statuses and check remediation steps after normalization
        const statusCounts = normalizedActions.reduce((acc, a) => {
          acc[a.status] = (acc[a.status] || 0) + 1;
          return acc;
        }, {} as Record<string, number>);
        const withSteps = normalizedActions.filter(a => a.remediation_steps && a.remediation_steps.length > 0).length;
        console.log('📊 loadFromBackend - Actions after normalization:', statusCounts, `| With steps: ${withSteps}/${normalizedActions.length}`);
      }

      this.dataLoaded = true;
      this.backendEnabled = true;

      console.log('✅ Successfully loaded all data from backend');
      return true;
    } catch (error) {
      console.error('❌ Failed to load from backend:', error);
      this.backendEnabled = false;
      return false;
    }
  }

  isBackendEnabled(): boolean {
    return this.backendEnabled && this.backendHealthy;
  }

  /**
   * Fetch incremental updates from backend (new KPIs, alerts, actions)
   * This is called periodically to refresh the data
   * Memory-optimized: smaller payloads, aggressive deduplication
   */
  async refreshFromBackend(): Promise<boolean> {
    if (!this.backendEnabled || !this.backendHealthy) {
      return false;
    }

    try {
      // Fetch recent data from backend (reduced payloads to prevent memory bloat)
      // Only fetch what we need for the UI (last few minutes of data)
      const [kpisResponse, alertsResponse, actionsResponse] = await Promise.all([
        getKPIs({ limit: 200 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 0 })), // Reduced from 500
        getAlerts({ limit: 100 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 0 })), // Reduced from 200
        getActions({ limit: 100 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 0 })), // Reduced from 200
      ]);

      // Debug log action status breakdown
      const statusCounts = actionsResponse.items.reduce((acc: Record<string, number>, a: { status: string }) => {
        const status = a.status?.toLowerCase() || 'unknown';
        acc[status] = (acc[status] || 0) + 1;
        return acc;
      }, {});
      console.log('📊 Actions fetched:', statusCounts, `total: ${actionsResponse.items.length}`);

      // Update KPIs - MERGE new KPIs with existing instead of replacing
      if (kpisResponse.items.length > 0) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const normalizedKPIs = kpisResponse.items.map((kpi: any) => ({
          metric_id: kpi.metric_id,
          node_id: kpi.node_id,
          timestamp: new Date(kpi.timestamp),
          ds_power_level_dbmv: kpi.ds_power_level_dbmv || 0,
          us_power_level_dbmv: kpi.us_power_level_dbmv || 0,
          ds_snr_db: kpi.ds_snr_db || 0,
          us_snr_db: kpi.us_snr_db || 0,
          ds_mer_db: kpi.ds_mer_db || 0,
          us_mer_db: kpi.us_mer_db || 0,
          fec_corrected_codewords: kpi.fec_corrected_codewords || 0,
          fec_uncorrected_codewords: kpi.fec_uncorrected_codewords || 0,
          t3_timeouts: kpi.t3_timeouts || 0,
          t4_timeouts: kpi.t4_timeouts || 0,
          downstream_throughput_mbps: kpi.downstream_throughput_mbps || kpi.throughput_mbps || 0,
          upstream_throughput_mbps: kpi.upstream_throughput_mbps || (kpi.throughput_mbps ? kpi.throughput_mbps * 0.3 : 0),
          latency_ms: kpi.latency_ms || 0,
          packet_loss_percent: kpi.packet_loss_percent || 0,
          jitter_ms: kpi.jitter_ms || 0,
          ds_channel_utilization_percent: kpi.ds_channel_utilization_percent || 0,
          us_channel_utilization_percent: kpi.us_channel_utilization_percent || 0,
          ofdm_utilization_percent: kpi.ofdm_utilization_percent || 0,
          active_modems: kpi.active_modems || 0,
          registered_modems: kpi.registered_modems || 0,
          offline_modems: kpi.offline_modems || 0,
          modems_with_flaps: kpi.modems_with_flaps || 0,
          node_temperature: kpi.node_temperature || 0,
          node_cpu_utilization: kpi.node_cpu_utilization || 0,
          node_memory_utilization: kpi.node_memory_utilization || 0,
          power_supply_voltage: kpi.power_supply_voltage || 0,
        })) as KPIMetrics[];

        // MERGE new KPIs with existing data instead of replacing
        // Build a Set of existing metric_ids to avoid duplicates
        const existingIds = new Set(this.kpiMetrics.map(kpi => kpi.metric_id));
        const newKPIs = normalizedKPIs.filter(kpi => !existingIds.has(kpi.metric_id));

        if (newKPIs.length > 0) {
          // Add new KPIs to the array
          this.kpiMetrics.push(...newKPIs);
          // Sort by timestamp
          this.kpiMetrics.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
          // Apply cleanup to maintain reasonable memory usage
          this.cleanupOldData();
        }
      }

      // Update alerts - MERGE instead of replacing (update existing, add new)
      if (alertsResponse.items.length > 0) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const normalizedAlerts = alertsResponse.items.map((alert: any) => ({
          alert_id: alert.alert_id,
          node_id: alert.node_id,
          timestamp: new Date(alert.timestamp),
          alert_type: (alert.type?.toLowerCase() || alert.alert_type?.toLowerCase() || 'node_outage') as Alert['alert_type'],
          severity: (alert.severity?.toLowerCase() || 'warning') as Alert['severity'],
          description: alert.description || alert.title || '',
          affected_kpis: alert.affected_kpis || [],
          ai_confidence: alert.ai_confidence || 0.8,
          model_name: alert.model_name || 'backend-generated',
          root_cause: alert.root_cause,
          status: (alert.status?.toLowerCase() || 'active') as Alert['status'],
          acknowledged_by: alert.acknowledged_by,
          resolved_at: alert.resolved_at ? new Date(alert.resolved_at) : undefined
        })) as Alert[];

        // MERGE alerts - update existing ones and add new ones (preserves historical alerts)
        normalizedAlerts.forEach(alert => this.alerts.set(alert.alert_id, alert));
      }

      // Update actions - MERGE instead of replacing (update existing, add new)
      if (actionsResponse.items.length > 0) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const normalizedActions = actionsResponse.items.map((action: any) => {
          const normalizedAction: SelfHealingAction = {
            action_id: action.action_id,
            alert_id: action.alert_id || '',
            node_id: action.node_id,
            timestamp: new Date(action.start_time || action.timestamp),
            action_type: (action.action_type?.toLowerCase() || 'load_balance') as SelfHealingAction['action_type'],
            action_details: action.action_details || { description: action.description },
            status: (action.status?.toLowerCase() || 'pending') as SelfHealingAction['status'],
            effectiveness_score: action.effectiveness_score,
            completion_time: action.end_time ? parseUTC(action.end_time) : undefined,
            rollback_available: action.rollback_available ?? false,
            automated: action.automated ?? true,
            // DON'T preserve old steps - always recalculate fresh based on current time
            // This ensures step progress updates on each refresh
            remediation_steps: undefined,
            current_step_index: undefined,
            step_started_at: undefined
          };

          // Initialize remediation steps fresh
          initializeRemediationSteps(normalizedAction);
          // Calculate step progress based on current time
          syncRemediationProgress(normalizedAction);
          return normalizedAction;
        });

        // MERGE actions - update existing ones and add new ones (preserves historical actions)
        normalizedActions.forEach(action => this.actions.set(action.action_id, action));

        // Debug: count statuses and check remediation steps after normalization
        const statusCounts = normalizedActions.reduce((acc, a) => {
          acc[a.status] = (acc[a.status] || 0) + 1;
          return acc;
        }, {} as Record<string, number>);
        const withSteps = normalizedActions.filter(a => a.remediation_steps && a.remediation_steps.length > 0).length;
        const inProgressWithSteps = normalizedActions.filter(a => a.status === 'in_progress' && a.remediation_steps?.length).length;
        if (statusCounts['in_progress'] > 0) {
          console.log('📊 Actions refresh:', statusCounts, `| With steps: ${withSteps}/${normalizedActions.length} | In-progress w/ steps: ${inProgressWithSteps}`);
        }
      }

      // Invalidate cache so UI gets fresh data
      invalidateCache();

      return true;
    } catch (error) {
      console.error('Failed to refresh from backend:', error);
      return false;
    }
  }

  /**
   * Fetch historical KPI data for a specific time range
   * Used when user expands time range in UI (on-demand loading)
   */
  async fetchHistoricalKPIs(hours: number): Promise<boolean> {
    if (!this.backendEnabled || !this.backendHealthy) {
      console.log('⚠️ Backend not available for historical data fetch');
      return false;
    }

    try {
      console.log(`📊 Fetching ${hours} hours of historical KPI data...`);

      const startTime = new Date();
      startTime.setHours(startTime.getHours() - hours);

      // Determine appropriate limit based on hours
      // ~1000 records per hour at 5-second intervals
      const estimatedRecords = Math.min(hours * 1000, 100000);

      const response = await getKPIs({
        limit: estimatedRecords,
        start_time: startTime.toISOString()
      });

      if (response.items.length > 0) {
        console.log(`📥 Received ${response.items.length} historical KPI records`);

        // Normalize and merge with existing data
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const normalizedKPIs = response.items.map((kpi: any) => ({
          metric_id: kpi.metric_id,
          node_id: kpi.node_id,
          timestamp: new Date(kpi.timestamp),
          ds_power_level_dbmv: kpi.ds_power_level_dbmv || 0,
          us_power_level_dbmv: kpi.us_power_level_dbmv || 0,
          ds_snr_db: kpi.ds_snr_db || 0,
          us_snr_db: kpi.us_snr_db || 0,
          ds_mer_db: kpi.ds_mer_db || 0,
          us_mer_db: kpi.us_mer_db || 0,
          fec_corrected_codewords: kpi.fec_corrected_codewords || 0,
          fec_uncorrected_codewords: kpi.fec_uncorrected_codewords || 0,
          t3_timeouts: kpi.t3_timeouts || 0,
          t4_timeouts: kpi.t4_timeouts || 0,
          downstream_throughput_mbps: kpi.downstream_throughput_mbps || kpi.throughput_mbps || 0,
          upstream_throughput_mbps: kpi.upstream_throughput_mbps || (kpi.throughput_mbps ? kpi.throughput_mbps * 0.3 : 0),
          latency_ms: kpi.latency_ms || 0,
          packet_loss_percent: kpi.packet_loss_percent || 0,
          jitter_ms: kpi.jitter_ms || 0,
          ds_channel_utilization_percent: kpi.ds_channel_utilization_percent || 0,
          us_channel_utilization_percent: kpi.us_channel_utilization_percent || 0,
          ofdm_utilization_percent: kpi.ofdm_utilization_percent || 0,
          active_modems: kpi.active_modems || 0,
          registered_modems: kpi.registered_modems || 0,
          offline_modems: kpi.offline_modems || 0,
          modems_with_flaps: kpi.modems_with_flaps || 0,
          node_temperature: kpi.node_temperature || 0,
          node_cpu_utilization: kpi.node_cpu_utilization || 0,
          node_memory_utilization: kpi.node_memory_utilization || 0,
          power_supply_voltage: kpi.power_supply_voltage || 0,
        })) as KPIMetrics[];

        // Merge with existing data (avoid duplicates)
        const existingIds = new Set(this.kpiMetrics.map(kpi => kpi.metric_id));
        const newKPIs = normalizedKPIs.filter(kpi => !existingIds.has(kpi.metric_id));

        if (newKPIs.length > 0) {
          this.kpiMetrics.push(...newKPIs);
          // Sort by timestamp
          this.kpiMetrics.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
          console.log(`✅ Added ${newKPIs.length} new KPI records (total: ${this.kpiMetrics.length})`);
        } else {
          console.log('ℹ️ No new KPI records to add (all already in store)');
        }

        // Cleanup old data if we exceed max
        this.cleanupOldData();
        return true;
      }

      return false;
    } catch (error) {
      console.error('Failed to fetch historical KPIs:', error);
      return false;
    }
  }

  /**
   * Fetch aggregated KPI data for charting (smaller payload than raw KPIs)
   */
  async fetchAggregatedKPIs(days: number, granularity: 'hourly' | 'daily' = 'daily'): Promise<AggregatedKPIsResponse | null> {
    if (!this.backendEnabled || !this.backendHealthy) {
      console.log('⚠️ Backend not available for aggregated KPI fetch');
      return null;
    }

    try {
      console.log(`📊 Fetching ${days}-day aggregated KPIs (${granularity})...`);
      const response = await getAggregatedKPIs({ days, granularity });
      console.log(`✅ Received ${response.data_points} aggregated data points`);
      return response;
    } catch (error) {
      console.error('Failed to fetch aggregated KPIs:', error);
      return null;
    }
  }

  async saveToPersistence(): Promise<void> {
    if (!this.persistenceEnabled) return;

    try {
      const savePromises = [];

      if (this.nodes.size > 0) {
        savePromises.push(savePersistedNodes(Array.from(this.nodes.values())));
      }

      if (this.kpiMetrics.length > 0) {
        // Save only recent KPIs - rely on backend NVMe for full history
        const maxPersist = DB_CONFIG.INDEXEDDB_MAX_RECORDS || 2000;
        const recentKPIs = this.kpiMetrics.slice(-maxPersist);
        savePromises.push(savePersistedKPIMetrics(recentKPIs, maxPersist));
      }

      if (this.alerts.size > 0) {
        savePromises.push(savePersistedAlerts(Array.from(this.alerts.values())));
      }

      if (this.actions.size > 0) {
        savePromises.push(savePersistedActions(Array.from(this.actions.values())));
      }

      // Save sensor data
      if (this.antennaSensors.size > 0) {
        savePromises.push(savePersistedAntennaSensors(Array.from(this.antennaSensors.values())));
      }

      if (this.weatherData.size > 0) {
        savePromises.push(savePersistedWeatherData(Array.from(this.weatherData.values())));
      }

      if (this.envSensors.size > 0) {
        savePromises.push(savePersistedEnvSensors(Array.from(this.envSensors.values())));
      }

      if (this.equipmentSensors.size > 0) {
        savePromises.push(savePersistedEquipmentSensors(Array.from(this.equipmentSensors.values())));
      }

      await Promise.all(savePromises);
      // Silent auto-save - only log errors
    } catch (error) {
      console.error('Failed to save data to persistence:', error);
    }
  }

  startAutoSave(intervalMs?: number): void {
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
    }

    // Use config value or default to 15 seconds for frequent NVMe writes
    const interval = intervalMs ?? DB_CONFIG.PERSIST_INTERVAL_MS ?? 15000;

    // Save frequently to NVMe AND run cleanup to keep memory low
    this.autoSaveInterval = setInterval(() => {
      // Run cleanup first to free memory
      this.cleanupOldData();
      this.saveToPersistence();

      // Log memory stats periodically for debugging (only when high)
      const stats = this.getMemoryStats();
      if (stats.kpiCount > DB_CONFIG.MAX_RECORDS * 0.8) {
        console.log(`📊 Memory: ${stats.kpiCount} KPIs, ${stats.alertCount} alerts, ${stats.actionCount} actions, ${stats.nodeCount} nodes`);
      }
    }, interval);

    console.log(`Auto-save enabled (every ${interval / 1000}s) - data persisted to NVMe via IndexedDB`);
  }

  // Get memory usage statistics for debugging
  getMemoryStats(): { kpiCount: number; alertCount: number; actionCount: number; nodeCount: number } {
    return {
      kpiCount: this.kpiMetrics.length,
      alertCount: this.alerts.size,
      actionCount: this.actions.size,
      nodeCount: this.nodes.size,
    };
  }

  stopAutoSave(): void {
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
      this.autoSaveInterval = null;
      console.log('Auto-save disabled');
    }
  }
}

// Singleton instance
export const store = new MemoryStore();
let dbInitialized = false;

// Exported API (matches database.ts interface)
export const initDatabase = async (): Promise<void> => {
  // Prevent double initialization (e.g., from React.StrictMode)
  if (dbInitialized) {
    return;
  }
  dbInitialized = true;

  console.log('Initializing memory store with persistence...');

  // Try to load persisted data
  const loaded = await store.loadFromPersistence();

  if (loaded) {
    console.log('Memory store initialized with persisted data');
  } else {
    console.log('Memory store initialized (no persisted data found)');
  }

  // Start auto-save - uses config interval (15s default) for frequent NVMe writes
  store.startAutoSave();
};

export const insertFiberNodes = async (nodes: FiberNode[]): Promise<void> => {
  store.insertNodes(nodes);
};

export const insertKPIMetrics = async (metrics: KPIMetrics[]): Promise<void> => {
  store.insertKPIMetrics(metrics);
};

export const insertAlerts = async (alerts: Alert[]): Promise<void> => {
  store.insertAlerts(alerts);
};

export const insertActions = async (actions: SelfHealingAction[]): Promise<void> => {
  store.insertActions(actions);
};

export const getFiberNodes = async (): Promise<FiberNode[]> => {
  return getCachedData(
    'all_nodes',
    () => store.getAllNodes(),
    CACHE_CONFIG.NODE_DATA
  );
};

export const getNetworkHealthSummary = async (): Promise<NetworkHealthSummary> => {
  return getCachedData(
    'network_health',
    () => store.getNetworkHealthSummary(),
    CACHE_CONFIG.NETWORK_HEALTH
  );
};

export const getActiveAlerts = async (): Promise<Alert[]> => {
  return getCachedData(
    'active_alerts',
    () => store.getActiveAlerts(),
    CACHE_CONFIG.ALERTS
  );
};

export const getRecentActions = async (limit: number = 50): Promise<SelfHealingAction[]> => {
  return getCachedData(
    `recent_actions_${limit}`,
    () => store.getRecentActions(limit),
    CACHE_CONFIG.ACTIONS
  );
};

// Get all actions - useful for dashboards that need full status breakdown
export const getAllActions = async (): Promise<SelfHealingAction[]> => {
  return store.getAllActions();
};

export const updateNodeStatus = async (nodeId: string, status: string): Promise<void> => {
  store.updateNodeStatus(nodeId, status as NodeStatus);
};

export const getRecentKPIMetrics = async (limit: number = 100): Promise<KPIMetrics[]> => {
  return store.getRecentKPIMetrics(limit);
};

// Historical data methods for charting (30-day analysis)
export const getDailyAggregatedKPIs = (days: number = 30) => {
  return store.getDailyAggregatedKPIs(days);
};

export const getAlertsForTimeRange = (days: number = 30) => {
  return store.getAlertsForTimeRange(days);
};

export const getActionsForTimeRange = (days: number = 30) => {
  return store.getActionsForTimeRange(days);
};

export const getKPIMetricsForTimeRange = (days: number = 30): KPIMetrics[] => {
  return store.getKPIMetricsForTimeRange(days);
};

// Persistence control methods
export const saveToPersistence = async (): Promise<void> => {
  return store.saveToPersistence();
};

export const loadFromPersistence = async (): Promise<boolean> => {
  return store.loadFromPersistence();
};

export const getAlertsByNode = async (nodeId: string): Promise<Alert[]> => {
  return store.getAlertsByNode(nodeId);
};

export const getActionsByNode = async (nodeId: string): Promise<SelfHealingAction[]> => {
  return store.getActionsByNode(nodeId);
};

export const getKPIMetricsForNode = async (nodeId: string, limit: number = 1000): Promise<KPIMetrics[]> => {
  return store.getKPIMetricsForNode(nodeId, limit);
};

// Sensor data exports
export const insertAntennaSensors = (sensors: AntennaSensorData[]): void => {
  store.insertAntennaSensors(sensors);
};

export const insertWeatherData = (weatherData: WeatherData[]): void => {
  store.insertWeatherData(weatherData);
};

export const insertEnvSensors = (sensors: EnvironmentalSensor[]): void => {
  store.insertEnvSensors(sensors);
};

export const insertEquipmentSensors = (sensors: EquipmentSensorData[]): void => {
  store.insertEquipmentSensors(sensors);
};

export const getAllSensorData = (nodeId: string) => {
  return store.getAllSensorData(nodeId);
};

export const getAllEquipmentSensors = (): EquipmentSensorData[] => {
  return store.getAllEquipmentSensors();
};

export const getAllAntennaSensors = (): AntennaSensorData[] => {
  return store.getAllAntennaSensors();
};

export const getAllEnvironmentalSensors = (): EnvironmentalSensor[] => {
  return store.getAllEnvironmentalSensors();
};

export const getAllWeatherData = (): WeatherData[] => {
  return store.getAllWeatherData();
};

export const isSensorDataLoaded = (): boolean => {
  return store.isSensorDataLoaded();
};

export const clearAllInMemoryData = (): void => {
  store.clear();
};

// Backend integration exports
export const loadFromBackend = (): Promise<boolean> => {
  return store.loadFromBackend();
};

export const refreshFromBackend = (): Promise<boolean> => {
  return store.refreshFromBackend();
};

export const checkBackendHealth = (): Promise<boolean> => {
  return store.checkBackendHealth();
};

export const isBackendEnabled = (): boolean => {
  return store.isBackendEnabled();
};

// Historical data loading (on-demand when user expands time range)
export const fetchHistoricalKPIs = (hours: number): Promise<boolean> => {
  return store.fetchHistoricalKPIs(hours);
};

// Aggregated KPI data for charts (smaller payload)
export const fetchAggregatedKPIs = (days: number, granularity: 'hourly' | 'daily' = 'daily') => {
  return store.fetchAggregatedKPIs(days, granularity);
};

