import { Activity, Clock, ArrowRight } from 'lucide-react';
import type { ConfigChangeLog } from '@/types';

interface Props {
  changes: ConfigChangeLog[];
}

const typeIcons: Record<string, string> = {
  automated: '🤖',
  manual: '👤',
  rollback: '↩️',
  compliance_fix: '🛡️',
};

export default function AgentActivityFeed({ changes }: Props) {
  return (
    <div className="bg-gray-800 rounded-xl p-5">
      <h3 className="text-sm font-medium text-gray-300 mb-4 flex items-center gap-2">
        <Activity className="w-4 h-4" /> Recent Activity ({changes.length})
      </h3>

      {changes.length === 0 ? (
        <p className="text-sm text-gray-500">No recent activity</p>
      ) : (
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {changes.map(change => (
            <div key={change.change_id} className="flex items-start gap-3 bg-gray-700/30 rounded-lg p-3">
              <span className="text-lg mt-0.5">{typeIcons[change.change_type] || '📝'}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-200 truncate">
                    {change.change_description || `${change.change_type} change`}
                  </span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    change.status === 'applied' ? 'bg-green-500/20 text-green-400' :
                    change.status === 'rolled_back' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {change.status}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                  <span>{change.device_id}</span>
                  <ArrowRight className="w-3 h-3" />
                  <span>{change.applied_by || 'system'}</span>
                  <span className="flex items-center gap-1 ml-auto">
                    <Clock className="w-3 h-3" />
                    {change.change_timestamp?.split('T')[0] || 'N/A'}
                  </span>
                </div>
                {change.change_request_id && (
                  <span className="text-xs text-blue-400 mt-0.5 inline-block">CR: {change.change_request_id}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
