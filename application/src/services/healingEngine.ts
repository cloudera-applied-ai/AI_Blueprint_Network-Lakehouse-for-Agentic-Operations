/**
 * Self-healing engine that applies remediation actions
 * and gradually restores node health with step-by-step workflow tracking
 */

import { FiberNode, SelfHealingAction, Alert, NodeStatus, ActionStatus, AlertStatus, RemediationStep, REMEDIATION_WORKFLOWS } from '@/types';
import { updateNodeStatus } from './memoryStore';
import { generateId } from '@/utils/helpers';

/**
 * Initialize remediation steps for an action based on action type
 */
export const initializeRemediationSteps = (action: SelfHealingAction): void => {
  if (action.remediation_steps && action.remediation_steps.length > 0) {
    return; // Already initialized
  }

  const workflow = REMEDIATION_WORKFLOWS[action.action_type];
  if (!workflow) {
    return;
  }

  action.remediation_steps = workflow.map((step, index) => ({
    step_id: generateId('STEP'),
    order: index + 1,
    name: step.name,
    description: step.description,
    status: 'pending' as const,
  }));
  action.current_step_index = 0;
};

/**
 * Get current step being executed
 */
export const getCurrentStep = (action: SelfHealingAction): RemediationStep | null => {
  if (!action.remediation_steps || action.current_step_index === undefined) {
    return null;
  }
  return action.remediation_steps[action.current_step_index] || null;
};

/**
 * Advance remediation steps based on action status and elapsed time
 * Called when refreshing actions from backend to sync step progress with backend status
 */
export const syncRemediationProgress = (action: SelfHealingAction): void => {
  if (!action.remediation_steps || action.remediation_steps.length === 0) {
    return;
  }

  const now = new Date();
  const actionAge = now.getTime() - action.timestamp.getTime();
  const totalSteps = action.remediation_steps.length;

  // If action is completed or failed, mark all steps accordingly
  if (action.status === ActionStatus.COMPLETED) {
    action.remediation_steps.forEach((step, idx) => {
      step.status = 'completed';
      step.completed_at = step.completed_at || new Date(action.timestamp.getTime() + ((idx + 1) / totalSteps) * actionAge);
      step.duration_ms = step.duration_ms || Math.floor(actionAge / totalSteps);
      step.result = step.result || getStepSuccessResultForSync(step);
    });
    action.current_step_index = totalSteps;
    return;
  }

  if (action.status === ActionStatus.FAILED) {
    // Mark steps up to the failure point
    const failurePoint = Math.floor(Math.random() * totalSteps);
    action.remediation_steps.forEach((step, idx) => {
      if (idx < failurePoint) {
        step.status = 'completed';
        step.completed_at = step.completed_at || new Date(action.timestamp.getTime() + ((idx + 1) / totalSteps) * actionAge);
        step.duration_ms = step.duration_ms || Math.floor(actionAge / totalSteps);
      } else if (idx === failurePoint) {
        step.status = 'failed';
        step.error = step.error || 'Action failed during execution';
      }
    });
    action.current_step_index = failurePoint;
    return;
  }

  // For in_progress actions, calculate which step should be active based on elapsed time
  if (action.status === ActionStatus.IN_PROGRESS) {
    // Assume each step takes ~3-4 seconds, total action ~25-35 seconds
    const avgStepDuration = 3500; // ms
    const currentStepIndex = Math.min(
      Math.floor(actionAge / avgStepDuration),
      totalSteps - 1
    );

    action.remediation_steps.forEach((step, idx) => {
      if (idx < currentStepIndex) {
        // Completed steps
        step.status = 'completed';
        step.started_at = step.started_at || new Date(action.timestamp.getTime() + idx * avgStepDuration);
        step.completed_at = step.completed_at || new Date(action.timestamp.getTime() + (idx + 1) * avgStepDuration);
        step.duration_ms = step.duration_ms || avgStepDuration;
        step.result = step.result || getStepSuccessResultForSync(step);
      } else if (idx === currentStepIndex) {
        // Current step in progress
        step.status = 'in_progress';
        step.started_at = step.started_at || new Date(action.timestamp.getTime() + idx * avgStepDuration);
      } else {
        // Future steps
        step.status = 'pending';
      }
    });
    action.current_step_index = currentStepIndex;
    action.step_started_at = action.remediation_steps[currentStepIndex]?.started_at;
    return;
  }

  // For pending actions, start the first step
  if (action.status === ActionStatus.PENDING) {
    action.current_step_index = 0;
    // Keep all steps as pending until action starts
  }
};

/**
 * Quick success result generator for sync (simpler than full generator)
 */
const getStepSuccessResultForSync = (step: RemediationStep): string => {
  const shortResults: Record<string, string> = {
    'Analyzing': 'Analysis complete',
    'Notifying': 'Notifications sent',
    'Graceful': 'Shutdown complete',
    'Initiating': 'Action initiated',
    'Hardware': 'Diagnostics passed',
    'Service': 'Services restored',
    'Verifying': 'Verified successfully',
    'KPI': 'KPIs validated',
    'Calculating': 'Parameters computed',
    'Updating': 'Updates applied',
    'Adjusting': 'Adjustments made',
    'Monitoring': 'Monitoring stable',
    'Baseline': 'Baseline recorded',
    'AI': 'AI analysis complete',
    'Safety': 'Safety checks passed',
    'Applying': 'Changes applied',
    'Performance': 'Performance improved',
    'Rollback': 'No rollback needed',
  };

  for (const [key, result] of Object.entries(shortResults)) {
    if (step.name.includes(key)) {
      return result;
    }
  }
  return 'Step completed';
};

/**
 * Process self-healing actions with step-by-step workflow
 */
export const processSelfHealingActions = async (
  actions: SelfHealingAction[],
  nodes: FiberNode[],
  alerts: Map<string, Alert>
): Promise<void> => {
  const now = new Date();
  let healedCount = 0;

  for (const action of actions) {
    // Only process pending or in-progress actions
    if (action.status === ActionStatus.COMPLETED || action.status === ActionStatus.FAILED) {
      continue;
    }

    // Initialize steps if not already done
    initializeRemediationSteps(action);

    const actionAge = now.getTime() - action.timestamp.getTime();

    if (action.status === ActionStatus.PENDING && actionAge > 2000) {
      // Start the action after 2 seconds (queue processing time)
      action.status = ActionStatus.IN_PROGRESS;
      action.step_started_at = now;

      // Start first step
      if (action.remediation_steps && action.remediation_steps.length > 0) {
        action.remediation_steps[0].status = 'in_progress';
        action.remediation_steps[0].started_at = now;
      }
    } else if (action.status === ActionStatus.IN_PROGRESS) {
      // Process step-by-step workflow
      const completed = await processRemediationSteps(action, now, nodes, alerts);

      if (completed) {
        // All steps completed - determine success/failure
        const success = Math.random() < (action.effectiveness_score || 80) / 100;

        if (success) {
          action.status = ActionStatus.COMPLETED;
          action.completion_time = now;

          // Apply healing to the node
          await healNode(action.node_id, action.effectiveness_score || 80, nodes);
          healedCount++;

          // Resolve the related alert
          const alert = alerts.get(action.alert_id);
          if (alert) {
            alert.status = AlertStatus.RESOLVED;
            alert.resolved_at = now;
          }
        } else {
          action.status = ActionStatus.FAILED;
          action.completion_time = now;

          // Mark last step as failed
          const lastStep = action.remediation_steps?.[action.remediation_steps.length - 1];
          if (lastStep) {
            lastStep.status = 'failed';
            lastStep.error = getStepFailureReason(action, lastStep);
          }
        }
      }
    }
  }

  // Only log significant healing activity
  if (healedCount >= 10) {
    console.log(`Self-healing: ${healedCount} nodes healed`);
  }
};

/**
 * Process individual remediation steps with realistic timing
 */
const processRemediationSteps = async (
  action: SelfHealingAction,
  now: Date,
  _nodes: FiberNode[],
  _alerts: Map<string, Alert>
): Promise<boolean> => {
  if (!action.remediation_steps || action.current_step_index === undefined) {
    return true; // No steps defined, complete immediately
  }

  const currentStep = action.remediation_steps[action.current_step_index];
  if (!currentStep) {
    return true; // All steps done
  }

  // If step is pending, start it
  if (currentStep.status === 'pending') {
    currentStep.status = 'in_progress';
    currentStep.started_at = now;
    action.step_started_at = now;
    return false;
  }

  // If step is in progress, check if enough time has passed
  if (currentStep.status === 'in_progress' && currentStep.started_at) {
    const stepAge = now.getTime() - currentStep.started_at.getTime();

    // Each step takes 2-4 seconds for visibility
    const stepDuration = 2000 + Math.random() * 2000;

    if (stepAge >= stepDuration) {
      // Complete this step
      currentStep.status = 'completed';
      currentStep.completed_at = now;
      currentStep.duration_ms = stepAge;
      currentStep.result = getStepSuccessResult(action, currentStep);

      // Move to next step
      action.current_step_index++;

      // Check if there are more steps
      if (action.current_step_index < action.remediation_steps.length) {
        const nextStep = action.remediation_steps[action.current_step_index];
        nextStep.status = 'in_progress';
        nextStep.started_at = now;
        action.step_started_at = now;
        return false;
      } else {
        // All steps completed
        return true;
      }
    }
  }

  return false;
};

/**
 * Generate success result message for a step
 */
const getStepSuccessResult = (_action: SelfHealingAction, step: RemediationStep): string => {
  const results: Record<string, string[]> = {
    'Analyzing System State': ['System state captured', 'Metrics collected successfully', 'State snapshot complete'],
    'Notifying Connected Users': ['Modem failover initiated for 127 subscribers', 'Subscriber notification sent', 'Graceful service migration in progress'],
    'Graceful Service Shutdown': ['Services stopped cleanly', 'All connections transferred', 'Shutdown complete'],
    'Initiating Soft Reboot': ['Reboot command sent', 'CMTS module restarting', 'Soft reset initiated'],
    'Hardware Self-Test': ['POST passed', 'Hardware diagnostics OK', 'All components healthy'],
    'Service Restoration': ['Services online', 'Node operational', 'DOCSIS channels active'],
    'Verifying Connectivity': ['Backhaul connected', 'Core network reachable', 'Trunk interfaces up'],
    'KPI Validation': ['KPIs within threshold', 'Performance nominal', 'Metrics validated'],
    'Analyzing Traffic Distribution': ['Traffic pattern analyzed', 'Load imbalance detected', 'Distribution mapped'],
    'Identifying Target Nodes': ['3 adjacent nodes identified', 'Capacity available on neighbors', 'Target nodes selected'],
    'Calculating RF Parameters': ['Parameters computed', 'Thresholds optimized', 'Channel bonding rules updated'],
    'Updating Channel Maps': ['Channel maps updated', 'Node relations modified', 'Frequency assignments refreshed'],
    'Adjusting Handover Margins': ['Margins adjusted by 3dB', 'Thresholds optimized', 'HO parameters tuned'],
    'Initiating User Migration': ['Migration started', '45 users handed over', 'Load redistributed'],
    'Monitoring Load Balance': ['Balance achieved', 'Load within 15% delta', 'Traffic stable'],
    'Baseline Measurement': ['Baseline recorded', 'Current params captured', 'Reference point set'],
    'AI Parameter Analysis': ['Optimal params computed', 'AI recommendation ready', 'Analysis complete'],
    'Safety Validation': ['Changes validated safe', 'Within operational limits', 'Safety check passed'],
    'Applying TX Power Adjustments': ['TX power adjusted -2dBm', 'Power level optimized', 'Transmission updated'],
    'Updating Antenna Tilt': ['Tilt adjusted to -6°', 'Electrical downtilt applied', 'Antenna configured'],
    'Performance Monitoring': ['KPIs improving', 'Coverage enhanced', 'Performance gains observed'],
    'Rollback Check': ['No rollback needed', 'Changes stable', 'Optimization successful'],
  };

  const stepResults = results[step.name];
  if (stepResults) {
    return stepResults[Math.floor(Math.random() * stepResults.length)];
  }
  return `Step ${step.order} completed successfully`;
};

/**
 * Generate failure reason for a step
 */
const getStepFailureReason = (action: SelfHealingAction, _step: RemediationStep): string => {
  const failures: Record<string, string[]> = {
    cell_reboot: ['Reboot timeout', 'Hardware not responding', 'Power fluctuation detected'],
    load_balance: ['Neighbors at capacity', 'Handover rejection', 'Config conflict'],
    parameter_optimization: ['Parameter rejected', 'KPIs degraded', 'Firmware incompatible'],
    antenna_adjustment: ['Motor unresponsive', 'Limit exceeded', 'Physical obstruction'],
    traffic_rerouting: ['Routes congested', 'QoS not met', 'Core rejected change'],
    ticket_creation: ['System unavailable', 'Duplicate ticket', 'Data incomplete'],
    neighbor_cell_expansion: ['Expansion rejected', 'Interference detected', 'Capacity exceeded'],
  };

  const typeFailures = failures[action.action_type] || ['Action failed'];
  return typeFailures[Math.floor(Math.random() * typeFailures.length)];
};

/**
 * Heal a node based on action effectiveness
 */
const healNode = async (
  nodeId: string,
  effectiveness: number,
  nodes: FiberNode[]
): Promise<void> => {
  const node = nodes.find((t) => t.node_id === nodeId);
  if (!node) return;

  // Healing progression based on effectiveness
  if (node.status === NodeStatus.OUTAGE) {
    if (effectiveness > 80) {
      // High effectiveness: outage → healthy
      node.status = NodeStatus.HEALTHY;
    } else if (effectiveness > 60) {
      // Medium effectiveness: outage → degraded
      node.status = NodeStatus.DEGRADED;
    }
    // Low effectiveness keeps it in outage, will retry
  } else if (node.status === NodeStatus.DEGRADED) {
    if (effectiveness > 70) {
      // Degraded → healthy
      node.status = NodeStatus.HEALTHY;
    }
    // Otherwise stays degraded
  }

  await updateNodeStatus(nodeId, node.status);
};

/**
 * Inject random failures with proper distribution
 * Only affects a small percentage of healthy nodes
 * IMPORTANT: Never allows more failures than healthy nodes (maintains 60%+ healthy)
 */
export const injectRandomFailures = async (nodes: FiberNode[]): Promise<void> => {
  const totalNodes = nodes.length;
  if (totalNodes === 0) return;

  const healthyNodes = nodes.filter((t) => t.status === NodeStatus.HEALTHY);
  const healthyCount = healthyNodes.length;
  const unhealthyCount = totalNodes - healthyCount;

  // Safety check: Ensure at least 60% of nodes remain healthy
  // If we're already below this threshold, don't inject more failures
  const MIN_HEALTHY_RATIO = 0.60;
  const currentHealthyRatio = healthyCount / totalNodes;

  if (currentHealthyRatio <= MIN_HEALTHY_RATIO) {
    // Too many failures already - skip injection this cycle
    console.log(`Skipping failure injection: healthy ratio ${(currentHealthyRatio * 100).toFixed(1)}% <= ${MIN_HEALTHY_RATIO * 100}% threshold`);
    return;
  }

  // Calculate max failures we can inject while staying above threshold
  const maxAllowedUnhealthy = Math.floor(totalNodes * (1 - MIN_HEALTHY_RATIO));
  const roomForNewFailures = maxAllowedUnhealthy - unhealthyCount;

  if (roomForNewFailures <= 0) {
    return; // No room for new failures
  }

  // Balanced failure rate: 0.5-0.8% of healthy nodes per cycle (about 5-8 nodes out of 1000)
  // But capped by how many failures we can afford
  const desiredFailureCount = Math.max(1, Math.floor(healthyNodes.length * (0.005 + Math.random() * 0.003)));
  const failureCount = Math.min(desiredFailureCount, roomForNewFailures);

  let actualFailures = 0;
  for (let i = 0; i < failureCount; i++) {
    const randomIndex = Math.floor(Math.random() * healthyNodes.length);
    const node = healthyNodes[randomIndex];

    if (!node || node.status !== NodeStatus.HEALTHY) continue;

    // Random failure type with weighted probabilities
    // Balanced distribution: outage, degraded, and maintenance
    const rand = Math.random();
    let newStatus: NodeStatus;

    if (rand < 0.30) {
      // 30% chance of outage
      newStatus = NodeStatus.OUTAGE;
    } else if (rand < 0.60) {
      // 30% chance of degraded
      newStatus = NodeStatus.DEGRADED;
    } else if (rand < 0.85) {
      // 25% chance of maintenance
      newStatus = NodeStatus.MAINTENANCE;
    } else {
      // 15% stay healthy
      continue;
    }

    node.status = newStatus;
    await updateNodeStatus(node.node_id, newStatus);
    actualFailures++;
  }
};

/**
 * Natural recovery for nodes in maintenance
 * Nodes in maintenance automatically return to healthy after some time
 */
export const processNaturalRecovery = async (nodes: FiberNode[]): Promise<void> => {
  let recoveredCount = 0;

  const maintenanceNodes = nodes.filter((t) => t.status === NodeStatus.MAINTENANCE);

  for (const node of maintenanceNodes) {
    // 10% chance per cycle to complete maintenance (slower for more visible states)
    if (Math.random() < 0.10) {
      node.status = NodeStatus.HEALTHY;
      await updateNodeStatus(node.node_id, NodeStatus.HEALTHY);
      recoveredCount++;
    }
  }

  // Occasionally, degraded nodes self-recover
  const degradedNodes = nodes.filter((t) => t.status === NodeStatus.DEGRADED);

  for (const node of degradedNodes) {
    // 5% chance per cycle to self-recover without action (slower for visibility)
    if (Math.random() < 0.05) {
      node.status = NodeStatus.HEALTHY;
      await updateNodeStatus(node.node_id, NodeStatus.HEALTHY);
      recoveredCount++;
    }
  }

  // Only log significant recovery activity
  if (recoveredCount >= 10) {
    console.log(`Natural recovery: ${recoveredCount} nodes recovered`);
  }
};
