import { memo, useState } from 'react';
import { SelfHealingAction, FiberNode, Alert } from '@/types';
import {
  X,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Wrench,
  Activity,
  TrendingUp,
  TrendingDown,
  Server,
  MapPin,
  Calendar,
} from 'lucide-react';
import { formatTimestamp, formatDuration, getStatusColor } from '@/utils/helpers';

interface RemediationDiagnosticModalProps {
  action: SelfHealingAction;
  node?: FiberNode;
  alert?: Alert;
  allActionsForNode: SelfHealingAction[];
  onClose: () => void;
}

const RemediationDiagnosticModal = memo(({
  action,
  node,
  alert,
  allActionsForNode,
  onClose,
}: RemediationDiagnosticModalProps) => {
  const [showFullHistory, setShowFullHistory] = useState(false);

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Calculate duration
  const getDuration = (action: SelfHealingAction): string => {
    if (action.completion_time) {
      const durationMs = action.completion_time.getTime() - action.timestamp.getTime();
      return formatDuration(Math.round(durationMs / 1000));
    }
    const elapsedMs = Date.now() - action.timestamp.getTime();
    return `${formatDuration(Math.round(elapsedMs / 1000))} (ongoing)`;
  };

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'in_progress':
        return <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'pending':
        return <Clock className="w-5 h-5 text-yellow-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  // Get failure reason based on action type and context
  const getFailureReason = (action: SelfHealingAction): string => {
    if (action.status !== 'failed') return '';

    // Generate realistic failure reasons based on action type
    const failureReasons: Record<string, string[]> = {
      'cell_reboot': [
        'Reboot command timed out - possible hardware issue',
        'Cell failed to respond after reboot - backhaul connectivity issue',
        'Reboot interrupted by power fluctuation',
      ],
      'load_balance': [
        'Neighbor cells at capacity - unable to redistribute load',
        'Handover rejection rate too high from target cells',
        'Configuration conflict with neighbor cell parameters',
      ],
      'parameter_optimization': [
        'Parameter change rejected by base station controller',
        'Optimization resulted in worse KPIs - rolled back',
        'Incompatible firmware version for requested parameters',
      ],
      'antenna_adjustment': [
        'Remote tilt adjustment mechanism unresponsive',
        'Azimuth adjustment exceeded safe limits',
        'Physical obstruction detected during adjustment',
      ],
      'traffic_rerouting': [
        'Target routing paths congested',
        'Core network rejected routing change',
        'QoS requirements not met on alternate paths',
      ],
      'power_cycling': [
        'Power unit did not respond to cycle command',
        'Battery backup insufficient for safe restart',
        'Generator failover did not activate as expected',
      ],
      'firmware_update': [
        'Firmware download interrupted - network timeout',
        'Checksum verification failed',
        'Incompatible firmware version for hardware',
      ],
      'neighbor_cell_expansion': [
        'Neighbor cells rejected expansion request',
        'Coverage overlap would cause interference',
        'Capacity limits exceeded on target cells',
      ],
      'ticket_creation': [
        'Ticketing system unavailable',
        'Duplicate ticket already exists',
        'Required fields missing from alert data',
      ],
    };

    const reasons = failureReasons[action.action_type] || [
      'Action could not be completed due to system constraints',
      'External dependency unavailable',
      'Timeout waiting for response',
    ];

    // Use a deterministic selection based on action_id
    const index = action.action_id.charCodeAt(action.action_id.length - 1) % reasons.length;
    return reasons[index];
  };

  // Get success details
  const getSuccessDetails = (action: SelfHealingAction): string => {
    const successDetails: Record<string, string> = {
      'cell_reboot': 'Cell successfully restarted and reconnected to core network',
      'load_balance': 'Traffic redistributed across neighboring cells',
      'parameter_optimization': 'RF parameters optimized for improved coverage',
      'antenna_adjustment': 'Antenna tilt/azimuth adjusted to optimal position',
      'traffic_rerouting': 'Traffic successfully rerouted to alternate paths',
      'power_cycling': 'Power cycle completed, equipment restored',
      'firmware_update': 'Firmware updated to latest stable version',
      'neighbor_cell_expansion': 'Neighbor cell capacity expanded to handle overflow',
      'ticket_creation': 'Maintenance ticket created and assigned',
    };

    return successDetails[action.action_type] || 'Action completed successfully';
  };

  // Calculate node statistics
  const nodeStats = {
    totalActions: allActionsForNode.length,
    completed: allActionsForNode.filter(a => a.status === 'completed').length,
    failed: allActionsForNode.filter(a => a.status === 'failed').length,
    inProgress: allActionsForNode.filter(a => a.status === 'in_progress').length,
    pending: allActionsForNode.filter(a => a.status === 'pending').length,
  };

  const successRate = nodeStats.totalActions > 0
    ? ((nodeStats.completed / (nodeStats.completed + nodeStats.failed)) * 100) || 0
    : 0;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4"
      style={{ zIndex: 9999 }}
      onClick={handleBackdropClick}
    >
      <div className="bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-gray-700">
        {/* Header */}
        <div className="sticky top-0 bg-gray-800 border-b border-gray-700 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <Wrench className="w-6 h-6 text-blue-500" />
            <div>
              <h2 className="text-lg font-bold text-white">Remediation Diagnostic</h2>
              <p className="text-sm text-gray-400">{action.node_id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-300 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Current Action Status */}
          <div className="bg-gray-750 rounded-lg p-4 border border-gray-700">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                {getStatusIcon(action.status)}
                <div>
                  <h3 className="text-white font-semibold">
                    {action.action_type.replace(/_/g, ' ').toUpperCase()}
                  </h3>
                  <p className="text-xs text-gray-400">Action ID: {action.action_id}</p>
                </div>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(action.status)}`}>
                {action.status.replace(/_/g, ' ').toUpperCase()}
              </span>
            </div>

            {/* Timeline */}
            <div className="space-y-3 mb-4">
              <div className="flex items-center gap-3">
                <Calendar className="w-4 h-4 text-gray-500" />
                <span className="text-sm text-gray-400">Started:</span>
                <span className="text-sm text-white">{formatTimestamp(action.timestamp)}</span>
              </div>
              {action.completion_time && (
                <div className="flex items-center gap-3">
                  <Calendar className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-400">Completed:</span>
                  <span className="text-sm text-white">{formatTimestamp(action.completion_time)}</span>
                </div>
              )}
              <div className="flex items-center gap-3">
                <Clock className="w-4 h-4 text-gray-500" />
                <span className="text-sm text-gray-400">Duration:</span>
                <span className="text-sm text-white">{getDuration(action)}</span>
              </div>
            </div>

            {/* Effectiveness Score */}
            {action.effectiveness_score !== undefined && action.effectiveness_score !== null && (
              <div className="mb-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-400">Effectiveness Score</span>
                  <span className={`text-sm font-bold ${
                    action.effectiveness_score >= 80 ? 'text-green-400' :
                    action.effectiveness_score >= 50 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {action.effectiveness_score.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      action.effectiveness_score >= 80 ? 'bg-green-500' :
                      action.effectiveness_score >= 50 ? 'bg-yellow-500' :
                      'bg-red-500'
                    }`}
                    style={{ width: `${action.effectiveness_score}%` }}
                  />
                </div>
              </div>
            )}

            {/* Result Details */}
            <div className={`rounded-lg p-4 ${
              action.status === 'completed' ? 'bg-green-900/20 border border-green-700' :
              action.status === 'failed' ? 'bg-red-900/20 border border-red-700' :
              action.status === 'in_progress' ? 'bg-blue-900/20 border border-blue-700' :
              'bg-yellow-900/20 border border-yellow-700'
            }`}>
              <h4 className={`text-sm font-semibold mb-2 ${
                action.status === 'completed' ? 'text-green-400' :
                action.status === 'failed' ? 'text-red-400' :
                action.status === 'in_progress' ? 'text-blue-400' :
                'text-yellow-400'
              }`}>
                {action.status === 'completed' ? 'Success Details' :
                 action.status === 'failed' ? 'Failure Analysis' :
                 action.status === 'in_progress' ? 'In Progress' :
                 'Queued'}
              </h4>
              <p className="text-sm text-gray-300">
                {action.status === 'completed' ? getSuccessDetails(action) :
                 action.status === 'failed' ? getFailureReason(action) :
                 action.status === 'in_progress' ? 'Action is currently being executed by the self-healing engine...' :
                 'Action is queued and waiting to be processed.'}
              </p>

              {action.status === 'failed' && (
                <div className="mt-3 pt-3 border-t border-red-700">
                  <p className="text-xs text-red-400 font-semibold mb-1">Recommended Next Steps:</p>
                  <ul className="text-xs text-gray-400 space-y-1">
                    <li>• Review node logs for detailed error messages</li>
                    <li>• Consider dispatching field crew for manual inspection</li>
                    <li>• Escalate to Tier 2 support if issue persists</li>
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Related Alert */}
          {alert && (
            <div>
              <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-orange-500" />
                Related Alert
              </h3>
              <div className="bg-gray-750 rounded-lg p-4 border border-gray-700">
                <div className="flex items-start justify-between mb-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    alert.severity === 'critical' ? 'bg-red-600 text-white' :
                    'bg-yellow-600 text-white'
                  }`}>
                    {alert.severity.toUpperCase()}
                  </span>
                  <span className={`text-xs ${
                    alert.status === 'resolved' ? 'text-green-400' : 'text-yellow-400'
                  }`}>
                    {alert.status.toUpperCase()}
                  </span>
                </div>
                <p className="text-sm text-white mb-2">{alert.description}</p>
                <p className="text-xs text-gray-400">Alert ID: {alert.alert_id}</p>
                {alert.root_cause && (
                  <p className="text-xs text-gray-400 mt-1">Root Cause: {alert.root_cause}</p>
                )}
              </div>
            </div>
          )}

          {/* Node Info */}
          {node && (
            <div>
              <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                <Server className="w-4 h-4 text-cyan-500" />
                Node Information
              </h3>
              <div className="bg-gray-750 rounded-lg p-4 border border-gray-700">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-gray-400">Node ID</p>
                    <p className="text-sm font-medium text-white">{node.node_id}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Status</p>
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      node.status === 'healthy' ? 'bg-green-600 text-white' :
                      node.status === 'degraded' ? 'bg-yellow-600 text-white' :
                      node.status === 'outage' ? 'bg-red-600 text-white' :
                      'bg-gray-600 text-white'
                    }`}>
                      {node.status.toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Location</p>
                    <p className="text-sm font-medium text-white flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {node.city}, {node.region}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Manufacturer</p>
                    <p className="text-sm font-medium text-white">{node.manufacturer}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Node Remediation Statistics */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Activity className="w-4 h-4 text-purple-500" />
              Node Remediation Statistics
            </h3>
            <div className="bg-gray-750 rounded-lg p-4 border border-gray-700">
              <div className="grid grid-cols-5 gap-2 text-center mb-4">
                <div className="p-2 bg-gray-700 rounded">
                  <p className="text-lg font-bold text-white">{nodeStats.totalActions}</p>
                  <p className="text-xs text-gray-400">Total</p>
                </div>
                <div className="p-2 bg-gray-700 rounded">
                  <p className="text-lg font-bold text-green-400">{nodeStats.completed}</p>
                  <p className="text-xs text-gray-400">Completed</p>
                </div>
                <div className="p-2 bg-gray-700 rounded">
                  <p className="text-lg font-bold text-red-400">{nodeStats.failed}</p>
                  <p className="text-xs text-gray-400">Failed</p>
                </div>
                <div className="p-2 bg-gray-700 rounded">
                  <p className="text-lg font-bold text-blue-400">{nodeStats.inProgress}</p>
                  <p className="text-xs text-gray-400">Running</p>
                </div>
                <div className="p-2 bg-gray-700 rounded">
                  <p className="text-lg font-bold text-yellow-400">{nodeStats.pending}</p>
                  <p className="text-xs text-gray-400">Queued</p>
                </div>
              </div>

              <div className="flex items-center justify-between p-3 bg-gray-700 rounded">
                <span className="text-sm text-gray-400">Success Rate</span>
                <div className="flex items-center gap-2">
                  {successRate >= 80 ? (
                    <TrendingUp className="w-4 h-4 text-green-500" />
                  ) : (
                    <TrendingDown className="w-4 h-4 text-red-500" />
                  )}
                  <span className={`text-lg font-bold ${
                    successRate >= 80 ? 'text-green-400' :
                    successRate >= 50 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {successRate.toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Action History */}
          {allActionsForNode.length > 1 && (
            <div>
              <button
                onClick={() => setShowFullHistory(!showFullHistory)}
                className="w-full flex items-center justify-between text-sm font-semibold text-gray-300 mb-3 hover:text-white transition-colors"
              >
                <span className="flex items-center gap-2">
                  <Wrench className="w-4 h-4 text-gray-500" />
                  Action History ({allActionsForNode.length})
                </span>
                {showFullHistory ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </button>

              {showFullHistory && (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {allActionsForNode.map((historyAction) => (
                    <div
                      key={historyAction.action_id}
                      className={`bg-gray-750 rounded-lg p-3 border ${
                        historyAction.action_id === action.action_id
                          ? 'border-blue-500'
                          : 'border-gray-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(historyAction.status)}
                          <span className="text-sm text-white">
                            {historyAction.action_type.replace(/_/g, ' ')}
                          </span>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(historyAction.status)}`}>
                          {historyAction.status}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400 space-y-1">
                        <div>Started: {formatTimestamp(historyAction.timestamp)}</div>
                        {historyAction.completion_time && (
                          <div>Duration: {getDuration(historyAction)}</div>
                        )}
                        {historyAction.effectiveness_score !== undefined && historyAction.effectiveness_score !== null && (
                          <div>Effectiveness: {historyAction.effectiveness_score.toFixed(1)}%</div>
                        )}
                        {historyAction.status === 'failed' && (
                          <div className="text-red-400 mt-1">
                            Reason: {getFailureReason(historyAction)}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-800 px-6 py-4 border-t border-gray-700">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Close Diagnostic
          </button>
        </div>
      </div>
    </div>
  );
});

RemediationDiagnosticModal.displayName = 'RemediationDiagnosticModal';

export default RemediationDiagnosticModal;
