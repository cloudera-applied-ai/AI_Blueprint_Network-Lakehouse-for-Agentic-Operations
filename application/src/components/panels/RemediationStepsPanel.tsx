import { SelfHealingAction, FiberNode, Alert, RemediationStep } from '@/types';
import {
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  AlertTriangle,
  Activity,
  ChevronRight,
} from 'lucide-react';
import { formatDuration } from '@/utils/helpers';

interface RemediationStepsPanelProps {
  action: SelfHealingAction;
  node?: FiberNode;
  alert?: Alert;
  compact?: boolean;
}


/**
 * Get status color classes
 */
const getStatusClasses = (status: RemediationStep['status']): { bg: string; text: string; border: string } => {
  switch (status) {
    case 'completed':
      return { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/50' };
    case 'in_progress':
      return { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/50' };
    case 'failed':
      return { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/50' };
    case 'skipped':
      return { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/50' };
    default:
      return { bg: 'bg-gray-700/50', text: 'text-gray-500', border: 'border-gray-600' };
  }
};

/**
 * Get status icon
 */
const getStatusIcon = (status: RemediationStep['status']) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    case 'in_progress':
      return <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />;
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-500" />;
    case 'skipped':
      return <ChevronRight className="w-4 h-4 text-gray-500" />;
    default:
      return <Clock className="w-4 h-4 text-gray-500" />;
  }
};

const RemediationStepsPanel = ({
  action,
  node,
  alert,
  compact = false,
}: RemediationStepsPanelProps) => {
  const steps = action.remediation_steps || [];
  const currentStepIndex = action.current_step_index ?? -1;

  // Calculate progress percentage — no useMemo; must recalculate every render
  // because parent ticks every 3s and syncs step progress based on elapsed time.
  const completedStepCount = steps.filter(s => s.status === 'completed').length;
  const inProgressCount = steps.filter(s => s.status === 'in_progress').length;
  const progressPercent = steps.length > 0
    ? Math.round(((completedStepCount + inProgressCount * 0.5) / steps.length) * 100)
    : 0;

  // Get elapsed time for current step
  const getCurrentStepElapsed = (step: RemediationStep): string => {
    if (step.status !== 'in_progress' || !step.started_at) return '';
    const elapsed = Date.now() - new Date(step.started_at).getTime();
    return formatDuration(Math.round(elapsed / 1000));
  };

  if (steps.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <div className="flex items-center gap-2 text-gray-400">
          <AlertTriangle className="w-4 h-4" />
          <span className="text-sm">No remediation steps defined for this action</span>
        </div>
      </div>
    );
  }

  if (compact) {
    // Compact view - just shows progress bar and current step
    const currentStep = steps[currentStepIndex];
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <RefreshCw className={`w-4 h-4 ${action.status === 'in_progress' ? 'text-blue-400 animate-spin' : 'text-gray-500'}`} />
            <span className="text-sm font-medium text-white">
              {action.action_type.replace(/_/g, ' ').toUpperCase()}
            </span>
          </div>
          <span className="text-xs text-gray-400">
            Step {currentStepIndex + 1}/{steps.length}
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-700 rounded-full h-2 mb-2">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${
              action.status === 'completed' ? 'bg-green-500' :
              action.status === 'failed' ? 'bg-red-500' : 'bg-blue-500'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Current step */}
        {currentStep && action.status === 'in_progress' && (
          <div className="flex items-center gap-2 text-sm">
            <RefreshCw className="w-3 h-3 text-blue-400 animate-spin" />
            <span className="text-blue-400 truncate">{currentStep.name}</span>
            <span className="text-xs text-gray-500 ml-auto">{getCurrentStepElapsed(currentStep)}</span>
          </div>
        )}
      </div>
    );
  }

  // Full view
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-500" />
            <h3 className="text-lg font-semibold text-white">Remediation Workflow</h3>
          </div>
          <span className={`px-2 py-1 rounded text-xs font-medium ${
            action.status === 'completed' ? 'bg-green-600 text-white' :
            action.status === 'failed' ? 'bg-red-600 text-white' :
            action.status === 'in_progress' ? 'bg-blue-600 text-white' :
            'bg-yellow-600 text-white'
          }`}>
            {action.status.replace(/_/g, ' ').toUpperCase()}
          </span>
        </div>

        {/* Node and Action Info */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Node:</span>
            <span className="text-white ml-2">{node?.node_id || action.node_id}</span>
          </div>
          <div>
            <span className="text-gray-500">Action:</span>
            <span className="text-white ml-2">{action.action_type.replace(/_/g, ' ')}</span>
          </div>
          {alert && (
            <>
              <div>
                <span className="text-gray-500">Alert:</span>
                <span className={`ml-2 ${alert.severity === 'critical' ? 'text-red-400' : 'text-yellow-400'}`}>
                  {alert.alert_type.replace(/_/g, ' ')}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Severity:</span>
                <span className={`ml-2 ${alert.severity === 'critical' ? 'text-red-400' : 'text-yellow-400'}`}>
                  {alert.severity.toUpperCase()}
                </span>
              </div>
            </>
          )}
        </div>

        {/* Overall Progress */}
        <div className="mt-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-400">Overall Progress</span>
            <span className="text-sm font-bold text-white">{progressPercent}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${
                action.status === 'completed' ? 'bg-green-500' :
                action.status === 'failed' ? 'bg-red-500' : 'bg-blue-500'
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Steps List */}
      <div className="p-4">
        <div className="relative">
          {/* Vertical connector line */}
          <div className="absolute left-[18px] top-0 bottom-0 w-0.5 bg-gray-700" />

          <div className="space-y-3">
            {steps.map((step, index) => {
              const statusClasses = getStatusClasses(step.status);
              const isActive = index === currentStepIndex && action.status === 'in_progress';

              return (
                <div
                  key={step.step_id}
                  className={`relative flex items-start gap-3 p-3 rounded-lg border transition-all ${
                    isActive
                      ? 'bg-blue-900/30 border-blue-500/50 shadow-lg shadow-blue-500/10'
                      : `${statusClasses.bg} ${statusClasses.border}`
                  }`}
                >
                  {/* Step number/icon */}
                  <div className={`relative z-10 flex items-center justify-center w-9 h-9 rounded-full ${
                    step.status === 'completed' ? 'bg-green-600' :
                    step.status === 'in_progress' ? 'bg-blue-600' :
                    step.status === 'failed' ? 'bg-red-600' :
                    'bg-gray-700'
                  }`}>
                    {step.status === 'completed' ? (
                      <CheckCircle2 className="w-5 h-5 text-white" />
                    ) : step.status === 'in_progress' ? (
                      <RefreshCw className="w-5 h-5 text-white animate-spin" />
                    ) : step.status === 'failed' ? (
                      <XCircle className="w-5 h-5 text-white" />
                    ) : (
                      <span className="text-sm font-bold text-gray-300">{step.order}</span>
                    )}
                  </div>

                  {/* Step content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-medium ${statusClasses.text} ${
                          step.status === 'pending' ? 'text-gray-400' : ''
                        }`}>
                          {step.name}
                        </span>
                        {step.status === 'in_progress' && (
                          <span className="text-xs text-blue-400 animate-pulse">Running...</span>
                        )}
                      </div>
                      {step.duration_ms && (
                        <span className="text-xs text-gray-500">
                          {formatDuration(Math.round(step.duration_ms / 1000))}
                        </span>
                      )}
                      {step.status === 'in_progress' && (
                        <span className="text-xs text-blue-400">
                          {getCurrentStepElapsed(step)}
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-gray-500 mt-0.5">{step.description}</p>

                    {/* Result or Error */}
                    {step.result && step.status === 'completed' && (
                      <div className="flex items-center gap-1 mt-1 text-xs text-green-400">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>{step.result}</span>
                      </div>
                    )}
                    {step.error && step.status === 'failed' && (
                      <div className="flex items-center gap-1 mt-1 text-xs text-red-400">
                        <XCircle className="w-3 h-3" />
                        <span>{step.error}</span>
                      </div>
                    )}
                  </div>

                  {/* Status indicator */}
                  <div className="flex-shrink-0">
                    {getStatusIcon(step.status)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Footer with effectiveness */}
      {action.effectiveness_score !== undefined && (
        <div className="p-4 border-t border-gray-700">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Effectiveness Score</span>
            <span className={`text-lg font-bold ${
              action.effectiveness_score >= 80 ? 'text-green-400' :
              action.effectiveness_score >= 50 ? 'text-yellow-400' :
              'text-red-400'
            }`}>
              {action.effectiveness_score.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
            <div
              className={`h-2 rounded-full ${
                action.effectiveness_score >= 80 ? 'bg-green-500' :
                action.effectiveness_score >= 50 ? 'bg-yellow-500' :
                'bg-red-500'
              }`}
              style={{ width: `${action.effectiveness_score}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default RemediationStepsPanel;
