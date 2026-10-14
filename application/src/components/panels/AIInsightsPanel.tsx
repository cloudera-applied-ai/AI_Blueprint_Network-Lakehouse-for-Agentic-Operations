import { memo, useMemo } from 'react';
import { AIInsight, InsightType, AIActionPlan } from '@/types/llm';
import {
  Brain,
  TrendingUp,
  AlertTriangle,
  Lightbulb,
  Activity,
  AlertCircle,
  Zap,
  CheckCircle,
  Clock,
  CheckCircle2
} from 'lucide-react';
import { formatTimestamp } from '@/utils/helpers';

interface AIInsightsPanelProps {
  insights: AIInsight[];
  actionPlans?: AIActionPlan[];
  activeAlertIds?: Set<string>;
}

const AIInsightsPanel = memo(({ insights, actionPlans = [], activeAlertIds = new Set() }: AIInsightsPanelProps) => {
  // Sort and categorize insights
  const { activeInsights, resolvedInsights } = useMemo(() => {
    const active: AIInsight[] = [];
    const resolved: AIInsight[] = [];

    insights.forEach(insight => {
      // Check if any related alerts are still active
      const hasActiveAlerts = insight.relatedAlerts?.some(alertId => activeAlertIds.has(alertId));
      if (hasActiveAlerts || !insight.relatedAlerts || insight.relatedAlerts.length === 0) {
        active.push(insight);
      } else {
        resolved.push(insight);
      }
    });

    // Sort each group by severity then timestamp
    const sortFn = (a: AIInsight, b: AIInsight) => {
      const severityOrder = { critical: 3, warning: 2, info: 1 };
      const severityDiff = severityOrder[b.severity] - severityOrder[a.severity];
      if (severityDiff !== 0) return severityDiff;
      return b.timestamp.getTime() - a.timestamp.getTime();
    };

    return {
      activeInsights: active.sort(sortFn),
      resolvedInsights: resolved.sort(sortFn)
    };
  }, [insights, activeAlertIds]);

  // Combined list with active first
  const sortedInsights = useMemo(() => {
    return [...activeInsights, ...resolvedInsights];
  }, [activeInsights, resolvedInsights]);

  // Get executing action plans
  const executingPlans = useMemo(() => {
    return actionPlans.filter(p => p.status === 'executing' || p.status === 'pending');
  }, [actionPlans]);

  const getInsightIcon = (type: InsightType) => {
    switch (type) {
      case InsightType.PATTERN_DETECTED:
        return Activity;
      case InsightType.ANOMALY_FORECAST:
        return TrendingUp;
      case InsightType.ROOT_CAUSE:
        return AlertCircle;
      case InsightType.OPTIMIZATION:
        return Lightbulb;
      case InsightType.CAPACITY_WARNING:
        return AlertTriangle;
      case InsightType.DEGRADATION_TREND:
        return TrendingUp;
      default:
        return Brain;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-500 bg-red-900/30 border-red-700';
      case 'warning':
        return 'text-yellow-500 bg-yellow-900/30 border-yellow-700';
      case 'info':
        return 'text-blue-500 bg-blue-900/30 border-blue-700';
      default:
        return 'text-gray-500 bg-gray-900/30 border-gray-700';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-green-500';
    if (confidence >= 0.7) return 'text-yellow-500';
    return 'text-orange-500';
  };

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Brain className="w-5 h-5 text-purple-500" />
          <h2 className="text-lg font-semibold text-white">
            AI Insights ({sortedInsights.length})
          </h2>
          {activeInsights.length > 0 && (
            <span className="text-xs px-2 py-0.5 rounded bg-red-900/50 text-red-300 border border-red-700">
              {activeInsights.length} Active
            </span>
          )}
          {resolvedInsights.length > 0 && (
            <span className="text-xs px-2 py-0.5 rounded bg-green-900/50 text-green-300 border border-green-700">
              {resolvedInsights.length} Resolved
            </span>
          )}
        </div>
        {sortedInsights.length > 0 && (
          <div className="text-xs text-gray-400">
            Last updated: {formatTimestamp(sortedInsights[0].timestamp)}
          </div>
        )}
      </div>

      <div className="space-y-4 flex-1 overflow-y-auto">
        {/* Show autonomous execution in progress */}
        {executingPlans.length > 0 && (
          <div className="space-y-3 mb-6">
            <div className="flex items-center gap-2 text-emerald-400 mb-2">
              <Zap className="w-4 h-4 animate-pulse" />
              <h3 className="text-sm font-semibold">Autonomous Execution In Progress</h3>
            </div>
            {executingPlans.map((plan) => {
              const completedSteps = plan.steps.filter(s => s.status === 'completed').length;
              const totalSteps = plan.steps.length;
              const progress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;

              return (
                <div
                  key={plan.id}
                  className="border border-emerald-700/50 bg-emerald-900/20 rounded-lg p-4"
                >
                  <div className="flex items-start gap-3 mb-3">
                    <Zap className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5 animate-pulse" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs px-2 py-0.5 rounded bg-emerald-800 text-emerald-200 uppercase font-medium">
                          {plan.status === 'executing' ? 'EXECUTING' : 'PENDING'}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-300">
                          {plan.priority} priority
                        </span>
                      </div>
                      <h4 className="text-sm font-semibold text-white mb-1">
                        {plan.rootCause}
                      </h4>
                      <p className="text-xs text-gray-400 mb-2">
                        {plan.affectedNodes.length} node(s) affected
                      </p>

                      {/* Progress bar */}
                      <div className="mb-2">
                        <div className="flex justify-between text-xs text-gray-400 mb-1">
                          <span>Progress: {completedSteps}/{totalSteps} steps</span>
                          <span>{progress.toFixed(0)}%</span>
                        </div>
                        <div className="w-full bg-gray-700 rounded-full h-2">
                          <div
                            className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                      </div>

                      {/* Current step */}
                      {plan.steps.map((step, idx) => {
                        if (step.status === 'in_progress') {
                          return (
                            <div key={step.id} className="flex items-center gap-2 mt-2 text-xs">
                              <Clock className="w-3 h-3 text-yellow-400 animate-spin" />
                              <span className="text-yellow-400">
                                Step {idx + 1}: {step.description}
                              </span>
                            </div>
                          );
                        }
                        return null;
                      })}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {sortedInsights.length === 0 && executingPlans.length === 0 ? (
          <div className="text-center py-12">
            <Brain className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-sm text-gray-500">No AI insights available yet</p>
            <p className="text-xs text-gray-600 mt-2">
              Enable AI agents in settings and wait for data analysis
            </p>
          </div>
        ) : (
          sortedInsights.map((insight) => {
            const Icon = getInsightIcon(insight.type);
            const severityColors = getSeverityColor(insight.severity);
            const confidenceColor = getConfidenceColor(insight.confidence);
            const isResolved = resolvedInsights.includes(insight);

            return (
              <div
                key={insight.id}
                className={`border rounded-lg p-4 ${severityColors} ${isResolved ? 'opacity-75' : ''}`}
              >
                {/* Header */}
                <div className="flex items-start gap-3 mb-3">
                  <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-300 uppercase font-medium">
                        {insight.type.replace(/_/g, ' ')}
                      </span>
                      {isResolved && (
                        <span className="text-xs px-2 py-0.5 rounded bg-green-900/50 text-green-300 border border-green-700 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          RESOLVED
                        </span>
                      )}
                      <span className={`text-xs font-medium ${confidenceColor}`}>
                        {(insight.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>
                    <h3 className="text-sm font-semibold text-white mb-2">
                      {insight.title}
                    </h3>
                  </div>
                </div>

                {/* Description */}
                <div className="mb-3 pl-8">
                  <p className="text-sm text-gray-300 leading-relaxed">
                    {insight.description}
                  </p>
                </div>

                {/* Autonomous Action Status or Recommendation */}
                {insight.recommendation && (
                  <div className="mb-3 pl-8">
                    <div className="flex items-start gap-2 p-3 bg-gray-800/50 rounded border border-gray-700">
                      <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-xs font-medium text-emerald-400 mb-1">
                          Autonomous Action Completed
                        </p>
                        <p className="text-xs text-gray-300">
                          {insight.recommendation}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Affected Nodes */}
                {insight.affectedNodes.length > 0 && (
                  <div className="pl-8">
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                      <span className="font-medium">Affected Nodes:</span>
                      <span>
                        {insight.affectedNodes.slice(0, 5).join(', ')}
                        {insight.affectedNodes.length > 5 &&
                          ` (+${insight.affectedNodes.length - 5} more)`
                        }
                      </span>
                    </div>
                  </div>
                )}

                {/* Metadata */}
                <div className="mt-3 pt-3 border-t border-gray-700 pl-8 flex items-center justify-between">
                  <span className="text-xs text-gray-500">
                    {formatTimestamp(insight.timestamp)}
                  </span>
                  {insight.relatedAlerts && insight.relatedAlerts.length > 0 && (
                    <span className="text-xs text-gray-500">
                      {insight.relatedAlerts.length} related alerts
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
});

AIInsightsPanel.displayName = 'AIInsightsPanel';

export default AIInsightsPanel;
