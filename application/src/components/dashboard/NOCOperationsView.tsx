import { memo, useMemo, useState, useEffect, useRef, useCallback } from 'react';
import { Alert, SelfHealingAction, FiberNode } from '@/types';
import { AIInsight, AIActionPlan, CrewDispatch } from '@/types/llm';
import { syncRemediationProgress, initializeRemediationSteps } from '@/services/remediationSteps';
import {
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Clock,
  MapPin,
  Users,
  Activity,
  RefreshCw,
  Bell,
  Wrench,
  Brain,
  TrendingUp,
  TrendingDown,
  Timer,
  ChevronRight,
  Building2,
  Maximize2,
} from 'lucide-react';
import { formatTimestamp } from '@/utils/helpers';
import RemediationDiagnosticModal from '../panels/RemediationDiagnosticModal';
import RemediationStepsPanel from '../panels/RemediationStepsPanel';

interface NOCOperationsViewProps {
  alerts: Alert[];
  actions: SelfHealingAction[];
  nodes: FiberNode[];
  aiInsights: AIInsight[];
  aiActionPlans: AIActionPlan[];
  crewDispatches: CrewDispatch[];
  onAlertClick?: (alert: Alert) => void;
  onNodeClick?: (node: FiberNode) => void;
}

type SeverityFilter = 'all' | 'critical' | 'warning';

const NOCOperationsView = memo(({
  alerts,
  actions,
  nodes,
  aiInsights,
  aiActionPlans,
  crewDispatches,
  onNodeClick,
}: NOCOperationsViewProps) => {
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all');
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [selectedAction, setSelectedAction] = useState<SelfHealingAction | null>(null);
  const [showWorkflowPanelId, setShowWorkflowPanelId] = useState<string | null>(null);

  // Tick counter — forces re-render every 3s so step progress updates visually.
  // No useMemo — step progress MUST be recalculated from elapsed time on every render.
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 3000);
    return () => clearInterval(id);
  }, []);

  // Sync remediation step progress for all visible actions based on current time.
  // Runs on EVERY render (no useMemo) so the 3s tick actually updates the UI.
  const activeActions = actions.filter(a => a.status === 'in_progress' || a.status === 'pending');
  for (const action of activeActions) {
    initializeRemediationSteps(action);
    syncRemediationProgress(action);
  }

  // Look up the live action for the workflow panel from the actions prop
  const showWorkflowPanel = showWorkflowPanelId
    ? actions.find(a => a.action_id === showWorkflowPanelId) ?? null
    : null;
  if (showWorkflowPanel) {
    initializeRemediationSteps(showWorkflowPanel);
    syncRemediationProgress(showWorkflowPanel);
  }

  const setShowWorkflowPanel = useCallback((action: SelfHealingAction | null) => {
    setShowWorkflowPanelId(action?.action_id ?? null);
  }, []);

  // Track recently completed actions to show completion celebration
  const [recentlyCompleted, setRecentlyCompleted] = useState<Map<string, { action: SelfHealingAction; completedAt: number }>>(new Map());
  const previousActionsRef = useRef<Map<string, string>>(new Map()); // action_id -> status

  // Detect newly completed actions
  useEffect(() => {
    const now = Date.now();
    const newCompletions = new Map(recentlyCompleted);

    actions.forEach(action => {
      const previousStatus = previousActionsRef.current.get(action.action_id);

      // Detect transition from in_progress to completed
      if (previousStatus === 'in_progress' && action.status === 'completed') {
        newCompletions.set(action.action_id, { action, completedAt: now });
      }
      // Also detect transition from in_progress to failed
      if (previousStatus === 'in_progress' && action.status === 'failed') {
        newCompletions.set(action.action_id, { action, completedAt: now });
      }

      // Update previous status
      previousActionsRef.current.set(action.action_id, action.status);
    });

    // Remove old completions (older than 10 seconds)
    newCompletions.forEach((value, key) => {
      if (now - value.completedAt > 10000) {
        newCompletions.delete(key);
      }
    });

    if (newCompletions.size !== recentlyCompleted.size) {
      setRecentlyCompleted(newCompletions);
    }
  }, [actions, recentlyCompleted]);

  // Auto-cleanup timer for recently completed
  useEffect(() => {
    if (recentlyCompleted.size === 0) return;

    const timer = setInterval(() => {
      const now = Date.now();
      setRecentlyCompleted(prev => {
        const updated = new Map(prev);
        let changed = false;
        updated.forEach((value, key) => {
          if (now - value.completedAt > 10000) {
            updated.delete(key);
            changed = true;
          }
        });
        return changed ? updated : prev;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [recentlyCompleted.size]);

  // Calculate comprehensive NOC metrics
  const nocMetrics = useMemo(() => {
    const now = new Date();
    const activeAlerts = alerts.filter(a => a.status === 'active');
    const criticalAlerts = activeAlerts.filter(a => a.severity === 'critical');
    const warningAlerts = activeAlerts.filter(a => a.severity === 'warning');

    // Calculate alert ages
    const alertAges = activeAlerts.map(a => (now.getTime() - new Date(a.timestamp).getTime()) / 60000);
    const avgAlertAge = alertAges.length > 0 ? alertAges.reduce((a, b) => a + b, 0) / alertAges.length : 0;
    const oldestAlert = alertAges.length > 0 ? Math.max(...alertAges) : 0;

    // Stale alerts (> 15 minutes without action)
    const staleAlerts = activeAlerts.filter(a => {
      const age = (now.getTime() - new Date(a.timestamp).getTime()) / 60000;
      const hasAction = actions.some(act => act.alert_id === a.alert_id);
      return age > 15 && !hasAction;
    });

    // Actions in progress
    const inProgressActions = actions.filter(a => a.status === 'in_progress' || a.status === 'pending');
    const completedActions = actions.filter(a => a.status === 'completed');
    const failedActions = actions.filter(a => a.status === 'failed');

    // Success rate (last 24 hours)
    const recentActions = actions.filter(a =>
      a.completion_time && (now.getTime() - new Date(a.completion_time).getTime()) < 24 * 60 * 60 * 1000
    );
    const successRate = recentActions.length > 0
      ? (recentActions.filter(a => a.status === 'completed').length / recentActions.length) * 100
      : 100;

    // Affected nodes and users
    const affectedNodeIds = new Set(activeAlerts.map(a => a.node_id));
    const affectedNodes = nodes.filter(t => affectedNodeIds.has(t.node_id));
    const totalAffectedUsers = affectedNodes.reduce((sum, t) => sum + (t.homes_active || 350) * 0.7, 0); // Assume 70% utilization

    // Regional breakdown
    const regionBreakdown = new Map<string, number>();
    activeAlerts.forEach(a => {
      const node = nodes.find(t => t.node_id === a.node_id);
      if (node) {
        regionBreakdown.set(node.region, (regionBreakdown.get(node.region) || 0) + 1);
      }
    });

    return {
      totalActive: activeAlerts.length,
      critical: criticalAlerts.length,
      warning: warningAlerts.length,
      stale: staleAlerts.length,
      avgAlertAge: Math.round(avgAlertAge),
      oldestAlert: Math.round(oldestAlert),
      inProgress: inProgressActions.length,
      completed: completedActions.length,
      failed: failedActions.length,
      successRate: Math.round(successRate),
      affectedNodes: affectedNodeIds.size,
      totalAffectedUsers: Math.round(totalAffectedUsers),
      regionBreakdown: Array.from(regionBreakdown.entries()).sort((a, b) => b[1] - a[1]),
      aiPlans: aiActionPlans.filter(p => p.status === 'executing' || p.status === 'pending').length,
      crewsDispatched: crewDispatches.filter(d => d.status !== 'completed').length,
    };
  }, [alerts, actions, nodes, aiActionPlans, crewDispatches]);

  // Filter alerts based on current filters
  const filteredAlerts = useMemo(() => {
    let filtered = alerts.filter(a => a.status === 'active'); // Only show active alerts

    if (severityFilter !== 'all') {
      filtered = filtered.filter(a => a.severity === severityFilter);
    }

    // Sort by severity (critical first) then by timestamp (newest first)
    return filtered.sort((a, b) => {
      if (a.severity === 'critical' && b.severity !== 'critical') return -1;
      if (b.severity === 'critical' && a.severity !== 'critical') return 1;
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });
  }, [alerts, severityFilter]);

  // Get node info for an alert
  const getNodeForAlert = (alert: Alert): FiberNode | undefined => {
    return nodes.find(t => t.node_id === alert.node_id);
  };

  // Get actions for an alert
  const getActionsForAlert = (alert: Alert): SelfHealingAction[] => {
    return actions.filter(a => a.alert_id === alert.alert_id);
  };

  // Calculate alert age
  const getAlertAge = (timestamp: Date): string => {
    const minutes = Math.round((Date.now() - new Date(timestamp).getTime()) / 60000);
    if (minutes < 60) return `${minutes}m`;
    if (minutes < 1440) return `${Math.round(minutes / 60)}h`;
    return `${Math.round(minutes / 1440)}d`;
  };

  // Get severity color
  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'critical': return 'text-red-500 bg-red-500/20 border-red-500/50';
      case 'warning': return 'text-yellow-500 bg-yellow-500/20 border-yellow-500/50';
      default: return 'text-blue-500 bg-blue-500/20 border-blue-500/50';
    }
  };

  // Get action status info
  const getActionStatusInfo = (alertId: string): { status: string; color: string; icon: React.ReactNode } => {
    const alertActions = actions.filter(a => a.alert_id === alertId);
    if (alertActions.length === 0) {
      return { status: 'No Action', color: 'text-gray-400', icon: <Clock className="w-4 h-4" /> };
    }

    const inProgress = alertActions.find(a => a.status === 'in_progress');
    if (inProgress) {
      return { status: 'Remediating', color: 'text-blue-400', icon: <RefreshCw className="w-4 h-4 animate-spin" /> };
    }

    const pending = alertActions.find(a => a.status === 'pending');
    if (pending) {
      return { status: 'Queued', color: 'text-yellow-400', icon: <Timer className="w-4 h-4" /> };
    }

    const completed = alertActions.find(a => a.status === 'completed');
    if (completed) {
      return { status: 'Resolved', color: 'text-green-400', icon: <CheckCircle2 className="w-4 h-4" /> };
    }

    const failed = alertActions.find(a => a.status === 'failed');
    if (failed) {
      return { status: 'Failed', color: 'text-red-400', icon: <AlertCircle className="w-4 h-4" /> };
    }

    return { status: 'Unknown', color: 'text-gray-400', icon: <Clock className="w-4 h-4" /> };
  };

  return (
    <div className="space-y-4">
      {/* NOC Summary Header */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
        {/* Critical Alerts */}
        <div className={`bg-gray-800 rounded-lg border p-4 ${nocMetrics.critical > 0 ? 'border-red-500/50 bg-red-900/20' : 'border-gray-700'}`}>
          <div className="flex items-center justify-between">
            <AlertCircle className={`w-5 h-5 ${nocMetrics.critical > 0 ? 'text-red-500' : 'text-gray-500'}`} />
            {nocMetrics.critical > 0 && <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />}
          </div>
          <p className={`text-2xl font-bold mt-2 ${nocMetrics.critical > 0 ? 'text-red-400' : 'text-white'}`}>
            {nocMetrics.critical}
          </p>
          <p className="text-xs text-gray-400">Critical Alerts</p>
        </div>

        {/* Warning Alerts */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <AlertTriangle className="w-5 h-5 text-yellow-500" />
          <p className="text-2xl font-bold mt-2 text-white">{nocMetrics.warning}</p>
          <p className="text-xs text-gray-400">Warnings</p>
        </div>

        {/* Stale Alerts */}
        <div className={`bg-gray-800 rounded-lg border p-4 ${nocMetrics.stale > 0 ? 'border-orange-500/50' : 'border-gray-700'}`}>
          <Timer className={`w-5 h-5 ${nocMetrics.stale > 0 ? 'text-orange-500' : 'text-gray-500'}`} />
          <p className={`text-2xl font-bold mt-2 ${nocMetrics.stale > 0 ? 'text-orange-400' : 'text-white'}`}>
            {nocMetrics.stale}
          </p>
          <p className="text-xs text-gray-400">Stale ({'>'}15m)</p>
        </div>

        {/* Remediation In Progress */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <Wrench className="w-5 h-5 text-blue-500" />
          <p className="text-2xl font-bold mt-2 text-white">{nocMetrics.inProgress}</p>
          <p className="text-xs text-gray-400">Remediating</p>
        </div>

        {/* Success Rate */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <div className="flex items-center gap-1">
            {nocMetrics.successRate >= 90 ? (
              <TrendingUp className="w-5 h-5 text-green-500" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-500" />
            )}
          </div>
          <p className={`text-2xl font-bold mt-2 ${nocMetrics.successRate >= 90 ? 'text-green-400' : 'text-red-400'}`}>
            {nocMetrics.successRate}%
          </p>
          <p className="text-xs text-gray-400">Success Rate</p>
        </div>

        {/* Affected Users */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <Users className="w-5 h-5 text-purple-500" />
          <p className="text-2xl font-bold mt-2 text-white">
            {nocMetrics.totalAffectedUsers > 1000
              ? `${(nocMetrics.totalAffectedUsers / 1000).toFixed(1)}K`
              : nocMetrics.totalAffectedUsers}
          </p>
          <p className="text-xs text-gray-400">Est. Affected Users</p>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Live Remediation Workflow - Takes 2 columns (MAIN PANEL) */}
        <div className="lg:col-span-2 bg-gray-800 rounded-lg border border-gray-700 flex flex-col min-h-[600px]">
          <div className="p-4 border-b border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-500 animate-pulse" />
                <h2 className="text-lg font-semibold text-white">Live Remediation Workflow</h2>
                <span className="px-2 py-0.5 bg-blue-900/50 text-blue-300 text-xs rounded-full">
                  {actions.filter(a => a.status === 'in_progress').length} active
                </span>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <span className="text-yellow-400">{actions.filter(a => a.status === 'pending').length} queued</span>
                <span className="text-green-400">{actions.filter(a => a.status === 'completed').length} completed</span>
                <span className="text-red-400">{actions.filter(a => a.status === 'failed').length} failed</span>
              </div>
            </div>
          </div>

          {/* Active Remediations Grid */}
          <div className="p-4 overflow-auto flex-1 flex flex-col">
            {(() => {
              // activeActions is pre-computed with synced step progress (runs every render)
              // Prioritize in_progress over pending for display order
              const sortedActions = [
                ...activeActions.filter(a => a.status === 'in_progress'),
                ...activeActions.filter(a => a.status === 'pending'),
              ];

              if (sortedActions.length === 0) {
                return (
                  <div className="flex-1 flex items-center justify-center">
                    <div className="text-center">
                      <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
                      <p className="text-lg text-gray-400">No active remediations</p>
                      <p className="text-sm text-gray-500 mt-1">All systems operating normally</p>
                    </div>
                  </div>
                );
              }

              return (
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                  {sortedActions.slice(0, 8).map((action) => {
                    const node = nodes.find(t => t.node_id === action.node_id);
                    const steps = action.remediation_steps || [];
                    const currentStepIndex = action.current_step_index ?? 0;
                    const currentStep = steps[currentStepIndex];
                    const completedSteps = steps.filter(s => s.status === 'completed').length;
                    const progressPercent = steps.length > 0 ? Math.round((completedSteps / steps.length) * 100) : 0;

                    return (
                      <div
                        key={action.action_id}
                        className={`rounded-lg border p-4 ${
                          action.status === 'in_progress'
                            ? 'bg-blue-900/20 border-blue-500/50'
                            : 'bg-yellow-900/20 border-yellow-500/50'
                        }`}
                      >
                        {/* Header */}
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            {action.status === 'in_progress' ? (
                              <RefreshCw className="w-5 h-5 text-blue-400 animate-spin" />
                            ) : (
                              <Timer className="w-5 h-5 text-yellow-400" />
                            )}
                            <div>
                              <span className="text-sm font-medium text-white">{action.node_id}</span>
                              {node && (
                                <span className="text-xs text-gray-500 ml-2">{node.city}, {node.region}</span>
                              )}
                            </div>
                          </div>
                          <button
                            onClick={() => setShowWorkflowPanel(action)}
                            className="p-1.5 hover:bg-gray-700 rounded transition-colors"
                            title="View full workflow"
                          >
                            <Maximize2 className="w-4 h-4 text-gray-400 hover:text-white" />
                          </button>
                        </div>

                        {/* Action Type */}
                        <p className="text-xs text-gray-400 mb-2 uppercase tracking-wide">
                          {action.action_type.replace(/_/g, ' ')}
                        </p>

                        {/* Progress Bar */}
                        <div className="mb-3">
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className={action.status === 'in_progress' ? 'text-blue-400' : 'text-yellow-400'}>
                              {action.status === 'in_progress' ? 'In Progress' : 'Queued'}
                            </span>
                            <span className="text-gray-300 font-medium">
                              Step {currentStepIndex + 1} / {steps.length}
                            </span>
                          </div>
                          <div className="w-full bg-gray-700 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full transition-all duration-500 ${
                                action.status === 'in_progress' ? 'bg-blue-500' : 'bg-yellow-500'
                              }`}
                              style={{ width: `${progressPercent}%` }}
                            />
                          </div>
                        </div>

                        {/* Current Step Details */}
                        {currentStep && action.status === 'in_progress' && (
                          <div className="bg-gray-800/50 rounded-lg p-3 mb-3">
                            <div className="flex items-start gap-3">
                              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                                <RefreshCw className="w-4 h-4 text-white animate-spin" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-blue-400">{currentStep.name}</p>
                                <p className="text-xs text-gray-500 mt-0.5">{currentStep.description}</p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Step Indicators */}
                        <div className="flex items-center gap-1.5">
                          {steps.map((step, idx) => (
                            <div
                              key={step.step_id}
                              className={`flex-1 h-1.5 rounded-full ${
                                step.status === 'completed' ? 'bg-green-500' :
                                step.status === 'in_progress' ? 'bg-blue-500 animate-pulse' :
                                step.status === 'failed' ? 'bg-red-500' :
                                'bg-gray-600'
                              }`}
                              title={`Step ${idx + 1}: ${step.name}`}
                            />
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })()}

            {actions.filter(a => a.status === 'in_progress' || a.status === 'pending').length > 8 && (
              <p className="text-center text-sm text-gray-500 mt-4">
                +{actions.filter(a => a.status === 'in_progress' || a.status === 'pending').length - 8} more active remediations
              </p>
            )}

            {/* Recently Completed/Failed - Celebration Section */}
            {recentlyCompleted.size > 0 && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  <span>Just Completed</span>
                </div>
                {Array.from(recentlyCompleted.values()).map(({ action, completedAt }) => {
                  const node = nodes.find(t => t.node_id === action.node_id);
                  const age = Math.round((Date.now() - completedAt) / 1000);
                  const isCompleted = action.status === 'completed';

                  return (
                    <div
                      key={action.action_id}
                      className={`rounded-lg border p-4 transition-all duration-500 animate-pulse ${
                        isCompleted
                          ? 'bg-green-900/30 border-green-500/70 shadow-lg shadow-green-500/20'
                          : 'bg-red-900/30 border-red-500/70 shadow-lg shadow-red-500/20'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                            isCompleted ? 'bg-green-600' : 'bg-red-600'
                          }`}>
                            {isCompleted ? (
                              <CheckCircle2 className="w-6 h-6 text-white" />
                            ) : (
                              <AlertCircle className="w-6 h-6 text-white" />
                            )}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-bold text-white">{action.node_id}</span>
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                                isCompleted ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
                              }`}>
                                {isCompleted ? 'COMPLETED' : 'FAILED'}
                              </span>
                            </div>
                            {node && (
                              <span className="text-xs text-gray-400">{node.city}, {node.region}</span>
                            )}
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-gray-400 uppercase tracking-wide">
                            {action.action_type.replace(/_/g, ' ')}
                          </p>
                          {action.effectiveness_score !== undefined && isCompleted && (
                            <p className={`text-sm font-bold ${
                              action.effectiveness_score >= 80 ? 'text-green-400' :
                              action.effectiveness_score >= 50 ? 'text-yellow-400' :
                              'text-red-400'
                            }`}>
                              {action.effectiveness_score.toFixed(0)}% effective
                            </p>
                          )}
                          <p className="text-xs text-gray-500">{age}s ago</p>
                        </div>
                      </div>

                      {/* Progress bar showing 100% completion */}
                      <div className="mt-3 w-full bg-gray-700 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all duration-1000 ${
                            isCompleted ? 'bg-green-500' : 'bg-red-500'
                          }`}
                          style={{ width: '100%' }}
                        />
                      </div>

                      {/* Step indicators all green/red */}
                      {action.remediation_steps && action.remediation_steps.length > 0 && (
                        <div className="flex items-center gap-1.5 mt-2">
                          {action.remediation_steps.map((step) => (
                            <div
                              key={step.step_id}
                              className={`flex-1 h-1.5 rounded-full ${
                                isCompleted ? 'bg-green-500' :
                                step.status === 'completed' ? 'bg-green-500' :
                                step.status === 'failed' ? 'bg-red-500' :
                                'bg-gray-600'
                              }`}
                              title={`${step.name}: ${step.status}`}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Sidebar - Alert Queue and Stats */}
        <div className="space-y-4">
          {/* Alert Queue (Compact) */}
          <div className="bg-gray-800 rounded-lg border border-gray-700">
            <div className="p-3 border-b border-gray-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bell className="w-4 h-4 text-red-500" />
                  <h3 className="text-sm font-semibold text-white">Alert Queue</h3>
                  <span className="px-1.5 py-0.5 bg-gray-700 text-gray-300 text-xs rounded-full">
                    {filteredAlerts.length}
                  </span>
                </div>
                <div className="flex items-center gap-1 bg-gray-700 rounded p-0.5">
                  <button
                    onClick={() => setSeverityFilter('all')}
                    className={`px-1.5 py-0.5 text-xs rounded ${severityFilter === 'all' ? 'bg-gray-600 text-white' : 'text-gray-400'}`}
                  >
                    All
                  </button>
                  <button
                    onClick={() => setSeverityFilter('critical')}
                    className={`px-1.5 py-0.5 text-xs rounded ${severityFilter === 'critical' ? 'bg-red-600 text-white' : 'text-gray-400'}`}
                  >
                    Crit
                  </button>
                  <button
                    onClick={() => setSeverityFilter('warning')}
                    className={`px-1.5 py-0.5 text-xs rounded ${severityFilter === 'warning' ? 'bg-yellow-600 text-white' : 'text-gray-400'}`}
                  >
                    Warn
                  </button>
                </div>
              </div>
            </div>
            <div className="overflow-auto" style={{ maxHeight: '300px' }}>
              {filteredAlerts.length === 0 ? (
                <div className="p-4 text-center">
                  <CheckCircle2 className="w-8 h-8 text-green-500 mx-auto mb-2" />
                  <p className="text-xs text-gray-400">No active alerts</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-700">
                  {filteredAlerts.slice(0, 10).map((alert) => {
                    const node = getNodeForAlert(alert);
                    const actionStatus = getActionStatusInfo(alert.alert_id);
                    const age = getAlertAge(alert.timestamp);

                    return (
                      <div
                        key={alert.alert_id}
                        onClick={() => setSelectedAlert(alert)}
                        className={`p-3 hover:bg-gray-750 cursor-pointer transition-colors ${
                          selectedAlert?.alert_id === alert.alert_id ? 'bg-gray-750' : ''
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium ${
                                alert.severity === 'critical' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                              }`}>
                                {alert.severity === 'critical' ? <AlertCircle className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                                {alert.severity}
                              </span>
                              <span className="text-xs text-gray-500">{age}</span>
                            </div>
                            <p className="text-sm text-white font-medium truncate">{alert.node_id}</p>
                            {node && (
                              <p className="text-xs text-gray-500 truncate">{node.city}, {node.region}</p>
                            )}
                          </div>
                          <div className={`flex items-center gap-1 text-xs ${actionStatus.color}`}>
                            {actionStatus.icon}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              {filteredAlerts.length > 10 && (
                <div className="p-2 text-center border-t border-gray-700">
                  <span className="text-xs text-gray-500">+{filteredAlerts.length - 10} more alerts</span>
                </div>
              )}
            </div>
          </div>
          {/* Selected Alert Details or Quick Stats */}
          {selectedAlert ? (
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-white">Alert Details</h3>
                <button
                  onClick={() => setSelectedAlert(null)}
                  className="text-gray-400 hover:text-white text-xs"
                >
                  Clear
                </button>
              </div>

              {(() => {
                const node = getNodeForAlert(selectedAlert);
                const alertActions = getActionsForAlert(selectedAlert);

                return (
                  <div className="space-y-4">
                    {/* Alert Info */}
                    <div className="space-y-2">
                      <div className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border ${getSeverityColor(selectedAlert.severity)}`}>
                        {selectedAlert.severity === 'critical' ? <AlertCircle className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                        {selectedAlert.severity.toUpperCase()}
                      </div>
                      <p className="text-sm text-white">{selectedAlert.description}</p>
                      <p className="text-xs text-gray-400">
                        Alert ID: {selectedAlert.alert_id}
                      </p>
                      <p className="text-xs text-gray-400">
                        Created: {formatTimestamp(selectedAlert.timestamp)}
                      </p>
                    </div>

                    {/* Node Info */}
                    {node && (
                      <div className="pt-3 border-t border-gray-700">
                        <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Node Information</h4>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div>
                            <p className="text-gray-500 text-xs">Node ID</p>
                            <p className="text-white font-mono">{node.node_id}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs">Region</p>
                            <p className="text-white">{node.region}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs">Location</p>
                            <p className="text-white">{node.city}, {node.state || node.region}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs">Node Type</p>
                            <p className="text-white">{node.node_type || 'N+0'}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs">Manufacturer</p>
                            <p className="text-white">{node.manufacturer}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs">DOCSIS Version</p>
                            <p className="text-white">{node.docsis_version || '3.1'}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs">Homes Active</p>
                            <p className="text-white">{node.homes_active || 0} subscribers</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs">Service Area</p>
                            <p className="text-white">{node.service_area || node.region}</p>
                          </div>
                        </div>
                        {onNodeClick && (
                          <button
                            onClick={() => onNodeClick(node)}
                            className="mt-3 w-full px-3 py-2 bg-gray-700 text-gray-300 text-sm rounded hover:bg-gray-600 flex items-center justify-center gap-2"
                          >
                            <MapPin className="w-4 h-4" />
                            View on Map
                          </button>
                        )}
                      </div>
                    )}

                    {/* Remediation Actions */}
                    <div className="pt-3 border-t border-gray-700">
                      <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Remediation Actions</h4>
                      {alertActions.length === 0 ? (
                        <p className="text-sm text-gray-500">No actions taken yet</p>
                      ) : (
                        <div className="space-y-2">
                          {alertActions.map((action) => (
                            <div key={action.action_id} className="bg-gray-750 rounded p-2">
                              <div className="flex items-center justify-between">
                                <span className="text-sm text-white">{action.action_type.replace(/_/g, ' ')}</span>
                                <span className={`text-xs ${
                                  action.status === 'completed' ? 'text-green-400' :
                                  action.status === 'in_progress' ? 'text-blue-400' :
                                  action.status === 'failed' ? 'text-red-400' :
                                  'text-yellow-400'
                                }`}>
                                  {action.status}
                                </span>
                              </div>
                              {action.effectiveness_score !== undefined && (
                                <p className="text-xs text-gray-400 mt-1">
                                  Effectiveness: {(action.effectiveness_score * 100).toFixed(0)}%
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}
            </div>
          ) : (
            /* Regional Breakdown */
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <Building2 className="w-4 h-4 text-blue-500" />
                Regional Breakdown
              </h3>
              {nocMetrics.regionBreakdown.length === 0 ? (
                <p className="text-sm text-gray-500">No active alerts by region</p>
              ) : (
                <div className="space-y-2">
                  {nocMetrics.regionBreakdown.map(([region, count]) => (
                    <div key={region} className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">{region}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{ width: `${(count / nocMetrics.totalActive) * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-white font-medium w-8 text-right">{count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Remediation Status Overview */}
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Wrench className="w-4 h-4 text-blue-500" />
              Remediation Summary
            </h3>

            {/* Status Summary */}
            <div className="grid grid-cols-4 gap-2 mb-4">
              <div className="text-center p-2 bg-gray-750 rounded">
                <p className="text-lg font-bold text-yellow-400">{actions.filter(a => a.status === 'pending').length}</p>
                <p className="text-xs text-gray-400">Queued</p>
              </div>
              <div className="text-center p-2 bg-gray-750 rounded">
                <p className="text-lg font-bold text-blue-400">{actions.filter(a => a.status === 'in_progress').length}</p>
                <p className="text-xs text-gray-400">Running</p>
              </div>
              <div className="text-center p-2 bg-gray-750 rounded">
                <p className="text-lg font-bold text-green-400">{actions.filter(a => a.status === 'completed').length}</p>
                <p className="text-xs text-gray-400">Completed</p>
              </div>
              <div className="text-center p-2 bg-gray-750 rounded">
                <p className="text-lg font-bold text-red-400">{actions.filter(a => a.status === 'failed').length}</p>
                <p className="text-xs text-gray-400">Failed</p>
              </div>
            </div>

            {/* Recent Completed/Failed */}
            <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Recent Activity</h4>
            {actions.length === 0 ? (
              <p className="text-sm text-gray-500">No remediation actions</p>
            ) : (
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {actions
                  .filter(a => a.status === 'completed' || a.status === 'failed')
                  .slice(0, 5)
                  .map((action) => (
                    <div
                      key={action.action_id}
                      onClick={() => setSelectedAction(action)}
                      className="flex items-center justify-between py-2 px-2 border-b border-gray-700 last:border-0 cursor-pointer hover:bg-gray-700 rounded transition-colors"
                    >
                      <div>
                        <p className="text-sm text-white">{action.node_id}</p>
                        <p className="text-xs text-gray-400">{action.action_type.replace(/_/g, ' ')}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        {action.status === 'completed' ? (
                          <CheckCircle2 className="w-4 h-4 text-green-400" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-red-400" />
                        )}
                        <span className={`text-xs ${
                          action.status === 'completed' ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {action.status === 'completed' ? 'Done' : 'Failed'}
                        </span>
                        <ChevronRight className="w-4 h-4 text-gray-500" />
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* AI Insights Summary */}
          {aiInsights.length > 0 && (
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <Brain className="w-4 h-4 text-purple-500" />
                AI Insights
              </h3>
              <div className="space-y-2">
                {aiInsights.slice(0, 3).map((insight, i) => (
                  <div key={i} className="p-2 bg-gray-750 rounded">
                    <p className="text-sm text-white">{insight.title}</p>
                    <p className="text-xs text-gray-400 mt-1 line-clamp-2">{insight.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Stats */}
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Activity className="w-4 h-4 text-green-500" />
              Session Stats
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-gray-500">Avg Alert Age</p>
                <p className="text-lg font-bold text-white">{nocMetrics.avgAlertAge}m</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Oldest Alert</p>
                <p className="text-lg font-bold text-white">{nocMetrics.oldestAlert}m</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Resolved (24h)</p>
                <p className="text-lg font-bold text-green-400">{nocMetrics.completed}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Failed (24h)</p>
                <p className="text-lg font-bold text-red-400">{nocMetrics.failed}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Remediation Diagnostic Modal */}
      {selectedAction && (
        <RemediationDiagnosticModal
          action={selectedAction}
          node={nodes.find(t => t.node_id === selectedAction.node_id)}
          alert={alerts.find(a => a.alert_id === selectedAction.alert_id)}
          allActionsForNode={actions.filter(a => a.node_id === selectedAction.node_id)}
          onClose={() => setSelectedAction(null)}
        />
      )}

      {/* Full Remediation Workflow Panel Modal */}
      {showWorkflowPanel && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4"
          style={{ zIndex: 9999 }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowWorkflowPanel(null);
          }}
        >
          <div className="max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <RemediationStepsPanel
              action={showWorkflowPanel}
              node={nodes.find(t => t.node_id === showWorkflowPanel.node_id)}
              alert={alerts.find(a => a.alert_id === showWorkflowPanel.alert_id)}
            />
            <button
              onClick={() => setShowWorkflowPanel(null)}
              className="mt-4 w-full px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
            >
              Close Workflow View
            </button>
          </div>
        </div>
      )}
    </div>
  );
});

NOCOperationsView.displayName = 'NOCOperationsView';

export default NOCOperationsView;
