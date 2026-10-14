import { memo, useState, useMemo } from 'react';
import { SelfHealingAction, ActionStatus, ActionType } from '@/types';
import { Wrench, CheckCircle, Clock, XCircle, Info } from 'lucide-react';
import { formatTimestamp, getStatusColor } from '@/utils/helpers';

interface ActionsPanelProps {
  actions: SelfHealingAction[];
}

const ActionsPanel = memo(({ actions }: ActionsPanelProps) => {
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

  const getActionIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return CheckCircle;
      case 'in_progress':
        return Clock;
      case 'failed':
        return XCircle;
      default:
        return Wrench;
    }
  };

  const formatActionDetails = (action: SelfHealingAction): { primary: string; reason: string } => {
    const details = action.action_details;

    switch (action.action_type) {
      case ActionType.PARAMETER_OPTIMIZATION: {
        const params = (details.parameters as string[])?.join(', ') || 'network parameters';
        return {
          primary: `Optimizing: ${params}`,
          reason: 'To improve signal quality and reduce interference'
        };
      }

      case ActionType.LOAD_BALANCE:
        return {
          primary: `Redistributing ${details.traffic_percentage}% traffic to ${details.target_cells} neighbor cells`,
          reason: 'To alleviate congestion and improve user experience'
        };

      case ActionType.NODE_REBOOT:
        return {
          primary: `${(details.reboot_type as string)?.charAt(0).toUpperCase()}${(details.reboot_type as string)?.slice(1)} reboot (${details.estimated_downtime})`,
          reason: 'To clear system errors and restore service'
        };

      case ActionType.RF_ADJUSTMENT:
        return {
          primary: `Tilt: ${details.tilt_adjustment}, Azimuth: ${details.azimuth_adjustment}`,
          reason: 'To optimize RF levels and reduce signal interference'
        };

      case ActionType.TRAFFIC_REROUTING:
        return {
          primary: `Rerouting via ${details.alternate_routes} paths (${details.expected_improvement} improvement)`,
          reason: 'To bypass congested routes and maintain QoS'
        };

      case ActionType.TICKET_CREATION:
        return {
          primary: `${(details.priority as string)?.toUpperCase()} priority ticket to ${details.assigned_to}`,
          reason: `Manual intervention required (SLA: ${details.sla})`
        };

      case ActionType.CAPACITY_EXPANSION:
        return {
          primary: `Adding ${details.new_neighbors} capacity channels (${details.capacity_margin || details.handover_margin} margin)`,
          reason: 'To improve downstream throughput capacity'
        };

      default:
        return {
          primary: 'Action in progress',
          reason: 'System optimization'
        };
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6 h-full flex flex-col">
      <h2 className="text-lg font-semibold text-white mb-4">
        Recent Self-Healing Actions ({filteredActions.length})
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
          onClick={() => setSelectedStatus(ActionStatus.COMPLETED)}
          className={`px-3 py-1 text-xs rounded-full transition-colors ${
            selectedStatus === ActionStatus.COMPLETED
              ? 'bg-green-600 text-white font-medium'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          Completed ({statusCounts[ActionStatus.COMPLETED]})
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
      </div>

      <div className="space-y-3 flex-1 overflow-y-auto">
        {filteredActions.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            {selectedStatus === 'all' ? 'No recent actions' : `No ${selectedStatus} actions`}
          </p>
        ) : (
          filteredActions.slice(0, 10).map((action) => {
            const Icon = getActionIcon(action.status);
            const actionDetails = formatActionDetails(action);
            return (
              <div
                key={action.action_id}
                className="border border-gray-700 rounded-lg p-3 bg-gray-750"
              >
                <div className="flex items-start gap-3">
                  <Icon className={`w-5 h-5 ${getStatusColor(action.status).split(' ')[0]} flex-shrink-0 mt-0.5`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(action.status)}`}>
                        {action.status}
                      </span>
                      <span className="text-xs text-gray-400">{action.node_id}</span>
                    </div>
                    <p className="text-sm text-white font-medium mb-2">
                      {action.action_type.replace(/_/g, ' ').toUpperCase()}
                    </p>

                    {/* Action Details */}
                    <div className="bg-gray-800 rounded p-2 mb-2 border border-gray-600">
                      <div className="flex items-start gap-2">
                        <Info className="w-3 h-3 text-blue-400 flex-shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-gray-300 font-medium mb-1">
                            {actionDetails.primary}
                          </p>
                          <p className="text-xs text-gray-400 italic">
                            {actionDetails.reason}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-400">
                        {formatTimestamp(action.timestamp)}
                      </span>
                      {action.effectiveness_score && (
                        <span className="text-xs text-green-500 font-medium">
                          {action.effectiveness_score.toFixed(0)}% effective
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
});

ActionsPanel.displayName = 'ActionsPanel';

export default ActionsPanel;
