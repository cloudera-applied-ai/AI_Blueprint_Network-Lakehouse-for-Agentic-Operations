import { memo } from 'react';
import { AIActionPlan } from '@/types/llm';
import { Brain, CheckCircle2, Clock, PlayCircle, XCircle, Lightbulb } from 'lucide-react';
import { formatTimestamp } from '@/utils/helpers';

interface AIActionPlansPanelProps {
  plans: AIActionPlan[];
}

const AIActionPlansPanel = memo(({ plans }: AIActionPlansPanelProps) => {
  const getPriorityColor = (priority: AIActionPlan['priority']) => {
    switch (priority) {
      case 'critical':
        return 'text-red-500 bg-red-900/30';
      case 'high':
        return 'text-orange-500 bg-orange-900/30';
      case 'medium':
        return 'text-yellow-500 bg-yellow-900/30';
      case 'low':
        return 'text-blue-500 bg-blue-900/30';
    }
  };

  const getStatusIcon = (status: AIActionPlan['status']) => {
    switch (status) {
      case 'pending':
        return <Clock className="w-4 h-4 text-gray-400" />;
      case 'executing':
        return <PlayCircle className="w-4 h-4 text-blue-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
    }
  };

  const getStepStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="w-3 h-3 text-gray-500" />;
      case 'in_progress':
        return <PlayCircle className="w-3 h-3 text-blue-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle2 className="w-3 h-3 text-green-500" />;
      case 'failed':
        return <XCircle className="w-3 h-3 text-red-500" />;
      case 'skipped':
        return <span className="w-3 h-3 text-gray-600">—</span>;
    }
  };

  const getStepTypeLabel = (type: string) => {
    switch (type) {
      case 'automated_healing':
        return '🔧 Auto Heal';
      case 'crew_dispatch':
        return '🚁 Crew Dispatch';
      case 'configuration_change':
        return '⚙️ Configuration';
      case 'monitoring':
        return '👁️ Monitoring';
      default:
        return type;
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Brain className="w-5 h-5 text-purple-500" />
          <h2 className="text-lg font-semibold text-white">
            AI Action Plans ({plans.length})
          </h2>
        </div>
        <div className="text-xs text-gray-400">
          {plans.filter((p) => p.status === 'executing').length} executing
        </div>
      </div>

      <div className="space-y-4 flex-1 overflow-y-auto">
        {plans.length === 0 ? (
          <div className="text-center py-12">
            <Brain className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-sm text-gray-500">No AI action plans yet</p>
            <p className="text-xs text-gray-600 mt-2">
              AI will create autonomous plans for critical alerts
            </p>
          </div>
        ) : (
          plans.map((plan) => (
            <div
              key={plan.id}
              className="border border-gray-700 rounded-lg p-4 bg-gray-750 hover:bg-gray-700 transition-colors"
            >
              {/* Plan Header */}
              <div className="flex items-start gap-3 mb-3">
                <div className="flex-shrink-0 mt-1">{getStatusIcon(plan.status)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={`text-xs px-2 py-0.5 rounded uppercase font-medium ${getPriorityColor(
                        plan.priority
                      )}`}
                    >
                      {plan.priority}
                    </span>
                    <span className="text-xs text-gray-500">
                      {(plan.confidence * 100).toFixed(0)}% confidence
                    </span>
                    <span className="text-xs text-gray-500">
                      {plan.affectedNodes.length} node(s)
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-white mb-1">
                    {plan.rootCause}
                  </h3>
                  <p className="text-xs text-gray-400">{formatTimestamp(plan.timestamp)}</p>
                </div>
              </div>

              {/* Reasoning */}
              {plan.reasoning && (
                <div className="mb-3 pl-7">
                  <div className="flex items-start gap-2 p-2 bg-gray-800/50 rounded text-xs">
                    <Lightbulb className="w-3 h-3 text-yellow-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-300">{plan.reasoning}</span>
                  </div>
                </div>
              )}

              {/* Steps */}
              <div className="pl-7 space-y-2">
                {plan.steps.map((step) => (
                  <div
                    key={step.id}
                    className="flex items-start gap-2 p-2 rounded bg-gray-800/50 hover:bg-gray-800 transition-colors"
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      {getStepStatusIcon(step.status)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium text-blue-400">
                          Step {step.order}
                        </span>
                        <span className="text-xs text-gray-500">
                          {getStepTypeLabel(step.type)}
                        </span>
                      </div>
                      <p className="text-xs text-gray-300">{step.description}</p>
                      {step.result && (
                        <p className="text-xs text-green-400 mt-1">✓ {step.result}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Execution Time */}
              {plan.executionStartTime && (
                <div className="mt-3 pt-3 border-t border-gray-700 pl-7 text-xs text-gray-500">
                  {plan.status === 'completed' && plan.completionTime ? (
                    <span>
                      Completed in{' '}
                      {Math.round(
                        (plan.completionTime.getTime() - plan.executionStartTime.getTime()) /
                          1000
                      )}
                      s
                    </span>
                  ) : (
                    <span>Started {formatTimestamp(plan.executionStartTime)}</span>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
});

AIActionPlansPanel.displayName = 'AIActionPlansPanel';

export default AIActionPlansPanel;
