import { memo, useState, useMemo } from 'react';
import { SelfHealingAction, ActionStatus, ActionType } from '@/types';
import { CheckCircle, Clock, XCircle, Circle, Wrench } from 'lucide-react';
import { formatTimestamp, getStatusColor } from '@/utils/helpers';

interface ActionTimelineProps {
  actions: SelfHealingAction[];
}

const ActionTimeline = memo(({ actions }: ActionTimelineProps) => {
  const [selectedStatus, setSelectedStatus] = useState<string>('all');

  const filteredActions = useMemo(() => {
    if (selectedStatus === 'all') {
      return actions;
    }
    return actions.filter(action => action.status === selectedStatus);
  }, [actions, selectedStatus]);

  const statusCounts = useMemo(() => {
    const counts = {
      all: actions.length,
      [ActionStatus.PENDING]: 0,
      [ActionStatus.IN_PROGRESS]: 0,
      [ActionStatus.COMPLETED]: 0,
      [ActionStatus.FAILED]: 0,
      [ActionStatus.ROLLED_BACK]: 0,
    };
    actions.forEach(action => {
      if (counts[action.status] !== undefined) {
        counts[action.status]++;
      }
    });
    return counts;
  }, [actions]);

  const getActionSteps = (action: SelfHealingAction): { label: string; completed: boolean }[] => {
    const baseSteps = [
      { label: 'Anomaly Detected', completed: true },
      { label: 'Action Initiated', completed: action.status !== ActionStatus.PENDING },
    ];

    switch (action.action_type) {
      case ActionType.PARAMETER_OPTIMIZATION:
        return [
          ...baseSteps,
          { label: 'Parameters Analyzed', completed: action.status === ActionStatus.IN_PROGRESS || action.status === ActionStatus.COMPLETED },
          { label: 'Configuration Applied', completed: action.status === ActionStatus.COMPLETED },
          { label: 'Verification', completed: action.status === ActionStatus.COMPLETED },
        ];

      case ActionType.NODE_REBOOT:
        return [
          ...baseSteps,
          { label: 'Pre-reboot Checks', completed: action.status === ActionStatus.IN_PROGRESS || action.status === ActionStatus.COMPLETED },
          { label: 'Rebooting Node', completed: action.status === ActionStatus.COMPLETED },
          { label: 'Post-reboot Validation', completed: action.status === ActionStatus.COMPLETED },
        ];

      case ActionType.LOAD_BALANCE:
        return [
          ...baseSteps,
          { label: 'Traffic Analysis', completed: action.status === ActionStatus.IN_PROGRESS || action.status === ActionStatus.COMPLETED },
          { label: 'Redistributing Load', completed: action.status === ActionStatus.COMPLETED },
          { label: 'Monitoring Performance', completed: action.status === ActionStatus.COMPLETED },
        ];

      case ActionType.TICKET_CREATION:
        return [
          ...baseSteps,
          { label: 'Ticket Generated', completed: action.status === ActionStatus.IN_PROGRESS || action.status === ActionStatus.COMPLETED },
          { label: 'Assigned to Team', completed: action.status === ActionStatus.COMPLETED },
        ];

      default:
        return [
          ...baseSteps,
          { label: 'Executing Action', completed: action.status === ActionStatus.IN_PROGRESS || action.status === ActionStatus.COMPLETED },
          { label: 'Verification', completed: action.status === ActionStatus.COMPLETED },
        ];
    }
  };

  const getCurrentStep = (action: SelfHealingAction): string => {
    const steps = getActionSteps(action);
    const currentStepIndex = steps.findIndex(step => !step.completed);

    if (action.status === ActionStatus.COMPLETED) {
      return `Completed - ${action.effectiveness_score?.toFixed(0)}% effective`;
    }
    if (action.status === ActionStatus.FAILED) {
      return 'Action Failed - Rollback Required';
    }
    if (action.status === ActionStatus.ROLLED_BACK) {
      return 'Action Rolled Back';
    }
    if (currentStepIndex === -1) {
      return 'Finalizing...';
    }
    return steps[currentStepIndex].label;
  };

  const getProgressPercentage = (action: SelfHealingAction): number => {
    const steps = getActionSteps(action);
    const completedSteps = steps.filter(s => s.completed).length;
    return (completedSteps / steps.length) * 100;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case ActionStatus.COMPLETED:
        return CheckCircle;
      case ActionStatus.IN_PROGRESS:
        return Clock;
      case ActionStatus.FAILED:
      case ActionStatus.ROLLED_BACK:
        return XCircle;
      default:
        return Circle;
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6 h-full flex flex-col">
      <h2 className="text-lg font-semibold text-white mb-4">
        Self-Healing Action Timeline ({filteredActions.length})
      </h2>

      {/* Status Filter */}
      <div className="flex gap-2 mb-4 flex-wrap">
        <button
          onClick={() => setSelectedStatus('all')}
          className={`px-3 py-1 text-xs rounded-full transition-colors ${
            selectedStatus === 'all'
              ? 'bg-blue-600 text-white font-medium'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          All ({statusCounts.all})
        </button>
        <button
          onClick={() => setSelectedStatus(ActionStatus.IN_PROGRESS)}
          className={`px-3 py-1 text-xs rounded-full transition-colors ${
            selectedStatus === ActionStatus.IN_PROGRESS
              ? 'bg-yellow-600 text-white font-medium'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          In Progress ({statusCounts[ActionStatus.IN_PROGRESS]})
        </button>
        <button
          onClick={() => setSelectedStatus(ActionStatus.COMPLETED)}
          className={`px-3 py-1 text-xs rounded-full transition-colors ${
            selectedStatus === ActionStatus.COMPLETED
              ? 'bg-green-600 text-white font-medium'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          Completed ({statusCounts[ActionStatus.COMPLETED]})
        </button>
      </div>

      <div className="space-y-4 flex-1 overflow-y-auto">
        {filteredActions.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            {selectedStatus === 'all' ? 'No recent actions' : `No ${selectedStatus} actions`}
          </p>
        ) : (
          filteredActions.slice(0, 20).map((action) => {
            const StatusIcon = getStatusIcon(action.status);
            const currentStep = getCurrentStep(action);
            const progress = getProgressPercentage(action);
            const steps = getActionSteps(action);

            return (
              <div
                key={action.action_id}
                className="border border-gray-700 rounded-lg p-4 bg-gray-750"
              >
                {/* Header */}
                <div className="flex items-start gap-3 mb-3">
                  <StatusIcon className={`w-5 h-5 ${getStatusColor(action.status).split(' ')[0]} flex-shrink-0 mt-0.5`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(action.status)}`}>
                        {action.status}
                      </span>
                      <span className="text-xs text-gray-400">{action.node_id}</span>
                      <span className="text-xs text-gray-500">•</span>
                      <span className="text-xs text-gray-400">{formatTimestamp(action.timestamp)}</span>
                    </div>
                    <p className="text-sm text-white font-medium mb-2">
                      {action.action_type.replace(/_/g, ' ').toUpperCase()}
                    </p>
                  </div>
                </div>

                {/* Current Step */}
                <div className="bg-gray-800 rounded p-3 mb-3 border border-gray-600">
                  <div className="flex items-center gap-2 mb-2">
                    <Wrench className="w-4 h-4 text-blue-400" />
                    <span className="text-xs font-semibold text-gray-300">Current Step:</span>
                  </div>
                  <p className="text-sm text-white font-medium">{currentStep}</p>
                </div>

                {/* Progress Bar */}
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-400">Progress</span>
                    <span className="text-xs text-gray-400">{progress.toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-500 ${
                        action.status === ActionStatus.COMPLETED
                          ? 'bg-green-500'
                          : action.status === ActionStatus.FAILED || action.status === ActionStatus.ROLLED_BACK
                          ? 'bg-red-500'
                          : 'bg-yellow-500'
                      }`}
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>

                {/* Step Timeline */}
                <div className="space-y-2">
                  {steps.map((step, index) => (
                    <div key={index} className="flex items-center gap-2">
                      {step.completed ? (
                        <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0" />
                      ) : (
                        <Circle className="w-3 h-3 text-gray-600 flex-shrink-0" />
                      )}
                      <span className={`text-xs ${step.completed ? 'text-gray-400' : 'text-gray-500'}`}>
                        {step.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
});

ActionTimeline.displayName = 'ActionTimeline';

export default ActionTimeline;
