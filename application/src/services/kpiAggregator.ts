/**
 * Aggregates KPI metrics into trend data for charting
 */

import { KPIMetrics, FiberNode, Region } from '@/types';
import { SERVICE_AREA_TO_REGION, REGION_TO_GEOGRAPHIC_REGION } from '@/constants';

export interface KPITrendPoint {
  timestamp: number;
  value: number;
}

export interface AggregatedKPITrends {
  ds_snr_db: KPITrendPoint[];
  downstream_throughput_mbps: KPITrendPoint[];
  packet_loss_percent: KPITrendPoint[];
  latency_ms: KPITrendPoint[];
  active_modems: KPITrendPoint[];
}

export interface KPICurrentValues {
  ds_snr_db: number;
  downstream_throughput_mbps: number;
  packet_loss_percent: number;
  latency_ms: number;
  active_modems: number;
}

/**
 * Aggregate KPI metrics into time-series data for charting
 * Groups metrics by time buckets and averages values
 */
export const aggregateKPITrends = (
  metrics: KPIMetrics[],
  bucketSizeMs: number = 5000, // 5 seconds by default (matches KPI generation interval)
  nodes?: FiberNode[], // Optional: for filtering by region
  regionFilter?: Region | 'all' // Optional: filter by specific region
): { trends: AggregatedKPITrends; current: KPICurrentValues } => {
  // Apply region filter if provided
  let filteredMetrics = metrics;
  if (nodes && regionFilter && regionFilter !== 'all') {
    const geoRegion = REGION_TO_GEOGRAPHIC_REGION[regionFilter as Region];
    const nodeIdsByRegion = new Set(
      nodes.filter(t => SERVICE_AREA_TO_REGION[t.region] === geoRegion).map(t => t.node_id)
    );
    filteredMetrics = metrics.filter(m => nodeIdsByRegion.has(m.node_id));
  }

  if (filteredMetrics.length === 0) {
    const emptyTrends: AggregatedKPITrends = {
      ds_snr_db: [],
      downstream_throughput_mbps: [],
      packet_loss_percent: [],
      latency_ms: [],
      active_modems: [],
    };
    const emptyCurrent: KPICurrentValues = {
      ds_snr_db: 0,
      downstream_throughput_mbps: 0,
      packet_loss_percent: 0,
      latency_ms: 0,
      active_modems: 0,
    };
    return { trends: emptyTrends, current: emptyCurrent };
  }

  // Group metrics by time buckets
  const buckets = new Map<number, KPIMetrics[]>();

  filteredMetrics.forEach((metric) => {
    const bucketTime = Math.floor(metric.timestamp.getTime() / bucketSizeMs) * bucketSizeMs;
    if (!buckets.has(bucketTime)) {
      buckets.set(bucketTime, []);
    }
    buckets.get(bucketTime)!.push(metric);
  });

  // Aggregate each bucket
  const sortedBuckets = Array.from(buckets.entries()).sort((a, b) => a[0] - b[0]);

  const trends: AggregatedKPITrends = {
    ds_snr_db: [],
    downstream_throughput_mbps: [],
    packet_loss_percent: [],
    latency_ms: [],
    active_modems: [],
  };

  sortedBuckets.forEach(([timestamp, bucketMetrics]) => {
    const count = bucketMetrics.length;

    trends.ds_snr_db.push({
      timestamp,
      value: bucketMetrics.reduce((sum, m) => sum + m.ds_snr_db, 0) / count,
    });

    trends.downstream_throughput_mbps.push({
      timestamp,
      value: bucketMetrics.reduce((sum, m) => sum + m.downstream_throughput_mbps, 0) / count,
    });

    trends.packet_loss_percent.push({
      timestamp,
      value: bucketMetrics.reduce((sum, m) => sum + m.packet_loss_percent, 0) / count,
    });

    trends.latency_ms.push({
      timestamp,
      value: bucketMetrics.reduce((sum, m) => sum + m.latency_ms, 0) / count,
    });

    trends.active_modems.push({
      timestamp,
      value: bucketMetrics.reduce((sum, m) => sum + m.active_modems, 0),
    });
  });

  // Get current values (most recent bucket)
  const latestMetrics = sortedBuckets[sortedBuckets.length - 1]?.[1] || [];
  const current: KPICurrentValues = {
    ds_snr_db: latestMetrics.reduce((sum, m) => sum + m.ds_snr_db, 0) / latestMetrics.length,
    downstream_throughput_mbps: latestMetrics.reduce((sum, m) => sum + m.downstream_throughput_mbps, 0) / latestMetrics.length,
    packet_loss_percent: latestMetrics.reduce((sum, m) => sum + m.packet_loss_percent, 0) / latestMetrics.length,
    latency_ms: latestMetrics.reduce((sum, m) => sum + m.latency_ms, 0) / latestMetrics.length,
    active_modems: latestMetrics.reduce((sum, m) => sum + m.active_modems, 0),
  };

  return { trends, current };
};
