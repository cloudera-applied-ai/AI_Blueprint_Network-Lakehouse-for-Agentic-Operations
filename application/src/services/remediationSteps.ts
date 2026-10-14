/**
 * Remediation step initialization and synchronization
 * Separated from healingEngine to avoid circular imports with memoryStore
 */

import { SelfHealingAction, ActionStatus, RemediationStep, REMEDIATION_WORKFLOWS } from '@/types';
import { generateId } from '@/utils/helpers';

/**
 * Initialize remediation steps for an action based on action type
 */
export const initializeRemediationSteps = (action: SelfHealingAction): void => {
  if (action.remediation_steps && action.remediation_steps.length > 0) {
    return; // Already initialized
  }

  // Ensure action_type is lowercase for workflow lookup
  const actionType = action.action_type?.toLowerCase() as SelfHealingAction['action_type'];
  const workflow = REMEDIATION_WORKFLOWS[actionType];

  if (!workflow) {
    // Create default steps for unknown action types
    console.warn(`⚠️ No workflow found for action type: "${action.action_type}" -> "${actionType}"`);
    action.remediation_steps = [
      { step_id: generateId('STEP'), order: 1, name: 'Analyzing Issue', description: 'Gathering diagnostic data', status: 'pending' },
      { step_id: generateId('STEP'), order: 2, name: 'Applying Fix', description: 'Executing remediation', status: 'pending' },
      { step_id: generateId('STEP'), order: 3, name: 'Verifying Result', description: 'Confirming resolution', status: 'pending' },
    ];
    action.current_step_index = 0;
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
 * Advance remediation steps based on action status and elapsed time
 * Called when refreshing actions from backend to sync step progress with backend status
 * This function RECALCULATES step progress from scratch based on current time
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
      step.result = step.result || getStepSuccessResult(step);
    });
    action.current_step_index = totalSteps;
    return;
  }

  if (action.status === ActionStatus.FAILED) {
    // Mark steps up to the failure point (use a deterministic failure point based on action_id)
    const hash = action.action_id.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
    const failurePoint = Math.min(hash % totalSteps, totalSteps - 1);
    action.remediation_steps.forEach((step, idx) => {
      if (idx < failurePoint) {
        step.status = 'completed';
        step.completed_at = step.completed_at || new Date(action.timestamp.getTime() + ((idx + 1) / totalSteps) * actionAge);
        step.duration_ms = step.duration_ms || Math.floor(actionAge / totalSteps);
        step.result = step.result || getStepSuccessResult(step);
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
    // Actions spend ~15s in PENDING before becoming IN_PROGRESS
    // Then spend ~60-90s in IN_PROGRESS before completing
    // Subtract pending time to get actual in-progress time
    const pendingTime = 15000; // 15 seconds in pending
    const inProgressAge = Math.max(0, actionAge - pendingTime);

    // Each step takes ~10 seconds for a 7-step workflow completing in ~70s
    const avgStepDuration = 10000; // ms (10 seconds per step)
    const currentStepIndex = Math.min(
      Math.floor(inProgressAge / avgStepDuration),
      totalSteps - 1
    );

    // Calculate base time: action timestamp + pending time
    const inProgressStartTime = action.timestamp.getTime() + pendingTime;

    action.remediation_steps.forEach((step, idx) => {
      if (idx < currentStepIndex) {
        // Completed steps
        step.status = 'completed';
        step.started_at = step.started_at || new Date(inProgressStartTime + idx * avgStepDuration);
        step.completed_at = step.completed_at || new Date(inProgressStartTime + (idx + 1) * avgStepDuration);
        step.duration_ms = step.duration_ms || avgStepDuration;
        step.result = step.result || getStepSuccessResult(step);
      } else if (idx === currentStepIndex) {
        // Current step in progress
        step.status = 'in_progress';
        step.started_at = step.started_at || new Date(inProgressStartTime + idx * avgStepDuration);
      } else {
        // Future steps
        step.status = 'pending';
      }
    });
    action.current_step_index = currentStepIndex;
    action.step_started_at = action.remediation_steps[currentStepIndex]?.started_at;
    return;
  }

  // For pending actions, keep at step 0
  if (action.status === ActionStatus.PENDING) {
    action.current_step_index = 0;
    // Keep all steps as pending until action starts
  }
};

/**
 * Quick success result generator for sync
 */
const getStepSuccessResult = (step: RemediationStep): string => {
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
    'Identifying': 'Targets identified',
    'Traffic': 'Traffic migrated',
    'Coverage': 'Coverage validated',
    'Current': 'State captured',
    'Motor': 'Systems checked',
    'VSWR': 'Impedance matched',
    'Gathering': 'Data collected',
    'Root': 'Cause documented',
    'Priority': 'Priority assigned',
    'Creating': 'Ticket created',
    'Assigning': 'Team assigned',
  };

  for (const [key, result] of Object.entries(shortResults)) {
    if (step.name.includes(key)) {
      return result;
    }
  }
  return 'Step completed';
};
