/**
 * Tracks real-time data flow metrics across the pipeline
 */

import { KPIMetrics, Alert, SelfHealingAction } from '@/types';

export interface DataFlowMetrics {
  ingestionRate: number;
  alertsGenerated: number;
  actionsTriggered: number;
  storageSize: number;
  processingLatency: number;
  activeConnections: number;
}

class DataFlowTracker {
  private kpiCount = 0;
  private lastKpiCount = 0;
  private lastUpdate = Date.now();
  private alertCount = 0;
  private actionCount = 0;
  private avgLatency = 0;
  private latencyMeasurements: number[] = [];

  /**
   * Record KPI ingestion
   */
  recordKPIBatch(count: number): void {
    this.kpiCount += count;
  }

  /**
   * Record alert generation with latency
   */
  recordAlert(latencyMs: number = 0): void {
    this.alertCount++;
    if (latencyMs > 0) {
      this.latencyMeasurements.push(latencyMs);
      if (this.latencyMeasurements.length > 100) {
        this.latencyMeasurements.shift();
      }
      this.avgLatency =
        this.latencyMeasurements.reduce((a, b) => a + b, 0) / this.latencyMeasurements.length;
    }
  }

  /**
   * Record self-healing action
   */
  recordAction(): void {
    this.actionCount++;
  }

  /**
   * Calculate current ingestion rate (KPIs per second)
   */
  private calculateIngestionRate(): number {
    const now = Date.now();
    const elapsed = (now - this.lastUpdate) / 1000; // seconds

    if (elapsed >= 1) {
      const kpisInPeriod = this.kpiCount - this.lastKpiCount;
      const rate = kpisInPeriod / elapsed;
      this.lastKpiCount = this.kpiCount;
      this.lastUpdate = now;
      return Math.round(rate);
    }

    return 0;
  }

  /**
   * Estimate storage size based on data in memory
   */
  private estimateStorageSize(
    kpiMetrics: KPIMetrics[],
    alerts: Alert[],
    actions: SelfHealingAction[]
  ): number {
    // Rough estimation: each KPI ~400 bytes, alert ~300 bytes, action ~200 bytes
    const kpiSize = kpiMetrics.length * 0.0004; // MB
    const alertSize = alerts.length * 0.0003; // MB
    const actionSize = actions.length * 0.0002; // MB

    return kpiSize + alertSize + actionSize;
  }

  /**
   * Get current metrics snapshot
   */
  getMetrics(
    kpiMetrics: KPIMetrics[],
    alerts: Alert[],
    actions: SelfHealingAction[],
    nodeCount: number
  ): DataFlowMetrics {
    return {
      ingestionRate: this.calculateIngestionRate(),
      alertsGenerated: this.alertCount,
      actionsTriggered: this.actionCount,
      storageSize: this.estimateStorageSize(kpiMetrics, alerts, actions),
      processingLatency: Math.round(this.avgLatency),
      activeConnections: nodeCount,
    };
  }

  /**
   * Reset counters (useful for testing)
   */
  reset(): void {
    this.kpiCount = 0;
    this.lastKpiCount = 0;
    this.lastUpdate = Date.now();
    this.alertCount = 0;
    this.actionCount = 0;
    this.avgLatency = 0;
    this.latencyMeasurements = [];
  }
}

// Singleton instance
export const dataFlowTracker = new DataFlowTracker();
