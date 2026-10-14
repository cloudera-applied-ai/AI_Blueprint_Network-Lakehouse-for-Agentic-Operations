/**
 * Edge data center anomaly flow API.
 */
import { apiRequest } from './baseClient';
import type { EdgeEvent, EdgeScenario, StagingStatus } from '../../types/edge';

export async function listEdgeScenarios(): Promise<EdgeScenario[]> {
  return apiRequest<EdgeScenario[]>('/edge/scenarios');
}

export async function listEdgeEvents(): Promise<EdgeEvent[]> {
  return apiRequest<EdgeEvent[]>('/edge/events');
}

export async function getEdgeEvent(executionId: string): Promise<EdgeEvent> {
  return apiRequest<EdgeEvent>(`/edge/events/${executionId}`);
}

export async function triggerEdgeEvent(
  headendId: string,
  scenarioId: string,
  pcapSource?: 'bundled' | 'synthesized'
): Promise<{ execution_id: string; status: string }> {
  return apiRequest('/edge/events', {
    method: 'POST',
    body: JSON.stringify({ headend_id: headendId, scenario_id: scenarioId, pcap_source: pcapSource }),
  });
}

export async function pollEdgeStaging(): Promise<{ processed: number }> {
  return apiRequest('/edge/poll', { method: 'POST' }, 300_000);
}

export async function getStagingStatus(): Promise<StagingStatus> {
  return apiRequest<StagingStatus>('/edge/staging/status');
}
