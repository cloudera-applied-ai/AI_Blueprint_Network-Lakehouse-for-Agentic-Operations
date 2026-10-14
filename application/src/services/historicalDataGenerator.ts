/**
 * Generates historical data for the past N days
 * Creates realistic patterns with daily and weekly variations
 */

import { FiberNode, KPIMetrics } from '@/types';
import { generateKPIMetrics } from './dataGenerator';
import { insertKPIMetrics } from './memoryStore';
import { DB_CONFIG } from '@/constants';

/**
 * Generate historical KPI data for the past N days
 * Samples data every 5 minutes to keep dataset manageable
 * Inserts data in batches to avoid memory issues
 */
export const generateAndInsertHistoricalKPIData = async (
  nodes: FiberNode[],
  daysBack: number = DB_CONFIG.INITIAL_HISTORY_DAYS
): Promise<void> => {
  const now = new Date();

  // Sample interval: every 5 minutes (instead of 5 seconds for real-time)
  // This gives us 288 samples per day per node
  const sampleIntervalMs = 5 * 60 * 1000; // 5 minutes
  const totalSamples = (daysBack * 24 * 60 * 60 * 1000) / sampleIntervalMs;
  const totalRecords = totalSamples * nodes.length;

  console.log(`Generating ${daysBack} days of historical data...`);
  console.log(`Total samples per node: ${totalSamples}`);
  console.log(`Total KPI records: ${totalRecords.toLocaleString()}`);

  // Generate and insert data in batches to avoid memory issues
  // Each batch represents 10 time samples across all nodes
  const batchSize = 10; // 10 time samples = 1000 nodes * 10 = 10,000 records per batch
  const totalBatches = Math.ceil(totalSamples / batchSize);
  let totalInserted = 0;

  for (let batch = 0; batch < totalBatches; batch++) {
    const batchStart = batch * batchSize;
    const batchEnd = Math.min(batchStart + batchSize, totalSamples);
    const batchData: KPIMetrics[] = [];

    for (let i = batchStart; i < batchEnd; i++) {
      // Calculate timestamp (going backwards from now)
      const timestamp = new Date(now.getTime() - (totalSamples - i) * sampleIntervalMs);

      // Generate KPIs for all nodes at this timestamp
      for (const node of nodes) {
        const kpi = generateKPIMetrics(node, timestamp);
        batchData.push(kpi);
      }
    }

    // Insert this batch
    await insertKPIMetrics(batchData);
    totalInserted += batchData.length;

    // Log progress every 50 batches
    if ((batch + 1) % 50 === 0 || batch === totalBatches - 1) {
      const progress = ((batch + 1) / totalBatches * 100).toFixed(1);
      console.log(`Historical data progress: ${progress}% complete (${totalInserted.toLocaleString()} records inserted)`);
    }
  }

  console.log(`Historical data generation complete: ${totalInserted.toLocaleString()} total records`);
};

/**
 * Legacy function for backward compatibility - use generateAndInsertHistoricalKPIData instead
 * @deprecated
 */
export const generateHistoricalKPIData = (
  nodes: FiberNode[],
  daysBack: number = DB_CONFIG.INITIAL_HISTORY_DAYS
): KPIMetrics[] => {
  console.warn('generateHistoricalKPIData is deprecated. Use generateAndInsertHistoricalKPIData instead.');
  const historicalData: KPIMetrics[] = [];
  const now = new Date();

  const sampleIntervalMs = 5 * 60 * 1000; // 5 minutes
  const totalSamples = (daysBack * 24 * 60 * 60 * 1000) / sampleIntervalMs;

  for (let i = 0; i < totalSamples; i++) {
    const timestamp = new Date(now.getTime() - (totalSamples - i) * sampleIntervalMs);
    for (const node of nodes) {
      const kpi = generateKPIMetrics(node, timestamp);
      historicalData.push(kpi);
    }
  }

  return historicalData;
};

/**
 * Check if historical data has already been initialized
 */
export const isHistoricalDataInitialized = (): boolean => {
  return localStorage.getItem('historical_data_initialized') === 'true';
};

/**
 * Mark historical data as initialized
 */
export const markHistoricalDataInitialized = (): void => {
  localStorage.setItem('historical_data_initialized', 'true');
};

/**
 * Clear historical data initialization flag (for testing)
 */
export const clearHistoricalDataFlag = (): void => {
  localStorage.removeItem('historical_data_initialized');
};
