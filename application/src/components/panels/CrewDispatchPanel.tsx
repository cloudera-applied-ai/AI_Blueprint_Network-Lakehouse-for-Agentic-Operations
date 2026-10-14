import { memo } from 'react';
import { CrewDispatch } from '@/types/llm';
import { Truck, MapPin, Clock, CheckCircle2, Navigation, Wrench } from 'lucide-react';
import { formatTimestamp } from '@/utils/helpers';

interface CrewDispatchPanelProps {
  dispatches: CrewDispatch[];
}

const CrewDispatchPanel = memo(({ dispatches }: CrewDispatchPanelProps) => {
  const getSeverityColor = (severity: CrewDispatch['severity']) => {
    switch (severity) {
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

  const getStatusIcon = (status: CrewDispatch['status']) => {
    switch (status) {
      case 'dispatched':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'en_route':
        return <Navigation className="w-4 h-4 text-blue-500 animate-pulse" />;
      case 'on_site':
        return <Wrench className="w-4 h-4 text-orange-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'cancelled':
        return <span className="w-4 h-4 text-gray-600">✗</span>;
    }
  };

  const getStatusLabel = (status: CrewDispatch['status']) => {
    switch (status) {
      case 'dispatched':
        return 'Dispatched';
      case 'en_route':
        return 'En Route';
      case 'on_site':
        return 'On Site';
      case 'completed':
        return 'Completed';
      case 'cancelled':
        return 'Cancelled';
    }
  };

  const getStatusColor = (status: CrewDispatch['status']) => {
    switch (status) {
      case 'dispatched':
        return 'text-yellow-400';
      case 'en_route':
        return 'text-blue-400';
      case 'on_site':
        return 'text-orange-400';
      case 'completed':
        return 'text-green-400';
      case 'cancelled':
        return 'text-gray-600';
    }
  };

  const getIssueTypeLabel = (type: CrewDispatch['issueType']) => {
    switch (type) {
      case 'hardware_failure':
        return '🔧 Hardware Failure';
      case 'antenna_alignment':
        return '📡 Antenna Alignment';
      case 'power_system':
        return '⚡ Power System';
      case 'connectivity':
        return '🔌 Connectivity';
      case 'preventive_maintenance':
        return '🛠️ Preventive Maintenance';
    }
  };

  const getProgressBar = (dispatch: CrewDispatch) => {
    const steps = ['dispatched', 'en_route', 'on_site', 'completed'];
    const currentIndex = steps.indexOf(dispatch.status);
    const progress = ((currentIndex + 1) / steps.length) * 100;

    return (
      <div className="w-full bg-gray-700 rounded-full h-1.5 mt-2">
        <div
          className="bg-blue-500 h-1.5 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        ></div>
      </div>
    );
  };

  const getTimeRemaining = (dispatch: CrewDispatch): string | null => {
    if (!dispatch.estimatedArrival || dispatch.status !== 'en_route') {
      return null;
    }

    const now = new Date();
    const eta = dispatch.estimatedArrival;
    const remaining = Math.max(0, Math.floor((eta.getTime() - now.getTime()) / 1000));

    if (remaining === 0) return 'Arriving now';
    if (remaining < 60) return `${remaining}s ETA`;
    return `${Math.floor(remaining / 60)}m ${remaining % 60}s ETA`;
  };

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Truck className="w-5 h-5 text-blue-500" />
          <h2 className="text-lg font-semibold text-white">
            Crew Dispatches ({dispatches.length})
          </h2>
        </div>
        <div className="text-xs text-gray-400">
          {dispatches.filter((d) => d.status === 'on_site').length} on-site
        </div>
      </div>

      <div className="space-y-4 flex-1 overflow-y-auto">
        {dispatches.length === 0 ? (
          <div className="text-center py-12">
            <Truck className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-sm text-gray-500">No crew dispatches yet</p>
            <p className="text-xs text-gray-600 mt-2">
              AI will dispatch crews for hardware issues
            </p>
          </div>
        ) : (
          dispatches.map((dispatch) => (
            <div
              key={dispatch.id}
              className="border border-gray-700 rounded-lg p-4 bg-gray-750 hover:bg-gray-700 transition-colors"
            >
              {/* Dispatch Header */}
              <div className="flex items-start gap-3 mb-3">
                <div className="flex-shrink-0 mt-1">{getStatusIcon(dispatch.status)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={`text-xs px-2 py-0.5 rounded uppercase font-medium ${getStatusColor(
                        dispatch.status
                      )} bg-gray-800`}
                    >
                      {getStatusLabel(dispatch.status)}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded uppercase font-medium ${getSeverityColor(
                        dispatch.severity
                      )}`}
                    >
                      {dispatch.severity}
                    </span>
                    {dispatch.aiInitiated && (
                      <span className="text-xs px-2 py-0.5 rounded bg-purple-900/30 text-purple-400">
                        AI
                      </span>
                    )}
                  </div>
                  <h3 className="text-sm font-semibold text-white mb-1">
                    {dispatch.assignedCrew || 'Unassigned'}
                  </h3>
                  <p className="text-xs text-gray-400">{getIssueTypeLabel(dispatch.issueType)}</p>
                </div>
              </div>

              {/* Description */}
              <div className="mb-3 pl-7">
                <p className="text-xs text-gray-300">{dispatch.description}</p>
              </div>

              {/* Location */}
              <div className="mb-3 pl-7">
                <div className="flex items-start gap-2 text-xs text-gray-400">
                  <MapPin className="w-3 h-3 flex-shrink-0 mt-0.5" />
                  <span>
                    {dispatch.location.city}, {dispatch.location.region}
                  </span>
                  <span className="text-gray-600">•</span>
                  <span className="text-gray-500">Node: {dispatch.nodeId}</span>
                </div>
              </div>

              {/* ETA or Work Log */}
              {dispatch.status === 'en_route' && getTimeRemaining(dispatch) && (
                <div className="mb-2 pl-7">
                  <div className="flex items-center gap-2 text-xs text-blue-400">
                    <Clock className="w-3 h-3" />
                    <span>{getTimeRemaining(dispatch)}</span>
                  </div>
                </div>
              )}

              {dispatch.status === 'completed' && dispatch.workLog && (
                <div className="mb-3 pl-7">
                  <div className="p-2 bg-green-900/20 border border-green-700 rounded text-xs">
                    <p className="text-green-400 font-medium mb-1">Work Completed</p>
                    <p className="text-gray-300">{dispatch.workLog}</p>
                  </div>
                </div>
              )}

              {/* Progress Bar */}
              {dispatch.status !== 'completed' && dispatch.status !== 'cancelled' && (
                <div className="pl-7">{getProgressBar(dispatch)}</div>
              )}

              {/* Metadata */}
              <div className="mt-3 pt-3 border-t border-gray-700 pl-7 flex items-center justify-between text-xs text-gray-500">
                <span>Dispatched {formatTimestamp(dispatch.dispatchTime)}</span>
                {dispatch.completionTime && (
                  <span>
                    Completed in{' '}
                    {Math.round(
                      (dispatch.completionTime.getTime() - dispatch.dispatchTime.getTime()) /
                        1000
                    )}
                    s
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
});

CrewDispatchPanel.displayName = 'CrewDispatchPanel';

export default CrewDispatchPanel;
