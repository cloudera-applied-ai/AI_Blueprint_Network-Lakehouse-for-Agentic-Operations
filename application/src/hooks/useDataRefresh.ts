import { useState, useEffect } from 'react';
import { FiberNode, Alert, SelfHealingAction } from '@/types';
import { AIInsight, AIActionPlan, CrewDispatch } from '@/types/llm';
import {
  getFiberNodes,
  getActiveAlerts,
  getAllActions,
  getRecentKPIMetrics,
  insertAntennaSensors,
  insertWeatherData,
  insertEnvSensors,
  insertEquipmentSensors,
  isBackendEnabled,
  refreshFromBackend,
} from '@/services/memoryStore';
import { generateSensorDataBatch } from '@/services/sensorDataGenerator';
import { UPDATE_INTERVALS } from '@/constants';
import { dataFlowTracker, DataFlowMetrics } from '@/services/dataFlowMetrics';
import { crewDispatchService } from '@/services/crewDispatchService';
import { getAIInsights, getAIActionPlans } from '@/services/apiClient';

interface UseDataRefreshReturn {
  /** Architecture/data flow metrics */
  archMetrics: DataFlowMetrics | null;
  /** Active alerts from backend */
  alerts: Alert[];
  /** Recent self-healing actions */
  actions: SelfHealingAction[];
  /** AI insights fetched from backend */
  aiInsights: AIInsight[];
  /** AI action plans fetched from backend */
  aiActionPlans: AIActionPlan[];
  /** Recent crew dispatches */
  crewDispatches: CrewDispatch[];
}

/**
 * Manages two polling loops that keep dashboard data fresh:
 *
 * 1. Backend refresh (5s) - pulls latest data from backend into the in-memory store
 * 2. UI data update (UPDATE_INTERVALS.UI_REFRESH) - reads from in-memory store,
 *    fetches AI insights/action plans, updates sensor data for affected nodes
 *
 * Both loops are paused while `loading` is true.
 */
export function useDataRefresh(
  loading: boolean,
  nodes: FiberNode[],
  setNodes: (nodes: FiberNode[]) => void,
): UseDataRefreshReturn {
  const [archMetrics, setArchMetrics] = useState<DataFlowMetrics | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [actions, setActions] = useState<SelfHealingAction[]>([]);
  const [aiInsights, setAiInsights] = useState<AIInsight[]>([]);
  const [aiActionPlans, setAiActionPlans] = useState<AIActionPlan[]>([]);
  const [crewDispatches, setCrewDispatches] = useState<CrewDispatch[]>([]);

  // Backend refresh interval - fetch from backend every 5 seconds
  useEffect(() => {
    if (loading || !isBackendEnabled()) return;

    const refreshBackendData = async () => {
      try {
        await refreshFromBackend();
        const updatedNodes = await getFiberNodes();
        if (updatedNodes.length > 0 && updatedNodes.length !== nodes.length) {
          setNodes(updatedNodes);
        }
      } catch (error) {
        console.error('Backend refresh error:', error);
      }
    };

    refreshBackendData();
    const backendInterval = setInterval(refreshBackendData, 5000);

    return () => clearInterval(backendInterval);
  }, [loading, nodes.length]);

  // Update architecture metrics, alerts, actions, AI data periodically
  useEffect(() => {
    if (loading) return;

    const updateData = async () => {
      const [kpiMetrics, activeAlerts, recentActions] = await Promise.all([
        getRecentKPIMetrics(200),
        getActiveAlerts(),
        getAllActions(),
      ]);

      // Debug: log action statuses
      const statusCounts = recentActions.reduce((acc, a) => {
        acc[a.status] = (acc[a.status] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);
      const withSteps = recentActions.filter(a => (a.remediation_steps?.length ?? 0) > 0);
      const inProgressWithSteps = withSteps.filter(a => a.status === 'in_progress');
      if (inProgressWithSteps.length > 0) {
        const sample = inProgressWithSteps[0];
        console.log('Dashboard actions:', statusCounts, `| In-progress w/steps: ${inProgressWithSteps.length}`,
          `| Sample steps: ${sample.remediation_steps?.length}, currentStep: ${sample.current_step_index}`);
      } else {
        console.log('Dashboard actions by status:', statusCounts);
      }

      const metrics = dataFlowTracker.getMetrics(kpiMetrics, activeAlerts, recentActions, nodes.length);
      setArchMetrics(metrics);
      setAlerts(activeAlerts);
      setActions(recentActions);

      // Update sensor data periodically (every ~5 updates)
      if (Math.random() < 0.2) {
        const affectedNodeIds = new Set([
          ...activeAlerts.map(a => a.node_id),
          ...recentActions.slice(0, 10).map(a => a.node_id),
        ]);

        if (affectedNodeIds.size > 0) {
          const nodesToUpdate = nodes.filter(t => affectedNodeIds.has(t.node_id));
          if (nodesToUpdate.length > 0) {
            const sensorBatch = generateSensorDataBatch(nodesToUpdate);
            insertAntennaSensors(sensorBatch.antennaSensors);
            insertWeatherData(sensorBatch.weatherData);
            insertEnvSensors(sensorBatch.environmentalSensors);
            insertEquipmentSensors(sensorBatch.equipmentSensors);
          }
        }
      }

      // Update AI UI state from backend
      try {
        const insightsResponse = await getAIInsights({ limit: 50 });
        if (insightsResponse.items) {
          const backendInsights: AIInsight[] = insightsResponse.items.map(item => ({
            id: item.insight_id || `insight-${item.id}`,
            type: (item.insight_type || 'pattern_detected') as AIInsight['type'],
            severity: (item.severity || 'info') as AIInsight['severity'],
            title: item.title,
            description: item.description,
            recommendation: item.recommendation,
            confidence: item.confidence,
            timestamp: new Date(item.created_at || Date.now()),
            affectedNodes: item.affected_node_ids || [],
            relatedAlerts: item.related_alert_ids || [],
            metadata: item.metadata,
          }));
          setAiInsights(backendInsights);
        }

        const plansResponse = await getAIActionPlans({ limit: 20 });
        if (plansResponse.items) {
          const backendPlans: AIActionPlan[] = plansResponse.items.map(item => ({
            id: item.plan_id,
            triggeredBy: item.alert_id,
            timestamp: new Date(item.created_at),
            rootCause: item.root_cause,
            priority: (item.priority || 'medium') as AIActionPlan['priority'],
            status: (item.status || 'pending') as AIActionPlan['status'],
            steps: (item.steps || []).map((step, idx) => ({
              id: `step-${item.plan_id}-${idx}`,
              order: step.step_number || idx + 1,
              type: 'automated_healing' as const,
              description: step.description,
              status: (step.status || 'pending') as 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped',
              startTime: step.started_at ? new Date(step.started_at) : undefined,
              completionTime: step.completed_at ? new Date(step.completed_at) : undefined,
            })),
            executionStartTime: item.started_at ? new Date(item.started_at) : undefined,
            completionTime: item.completed_at ? new Date(item.completed_at) : undefined,
            confidence: 0.8,
            reasoning: item.failure_reason || '',
            affectedNodes: [item.node_id],
          }));
          setAiActionPlans(backendPlans);
        }

        crewDispatchService.processDispatches();
        crewDispatchService.cleanup();
        setCrewDispatches(crewDispatchService.getAllDispatches().slice(0, 20));
      } catch (error) {
        console.error('Failed to fetch AI data from backend:', error);
      }
    };

    updateData();
    const interval = setInterval(updateData, UPDATE_INTERVALS.UI_REFRESH);

    return () => clearInterval(interval);
  }, [loading, nodes.length]);

  return {
    archMetrics,
    alerts,
    actions,
    aiInsights,
    aiActionPlans,
    crewDispatches,
  };
}
