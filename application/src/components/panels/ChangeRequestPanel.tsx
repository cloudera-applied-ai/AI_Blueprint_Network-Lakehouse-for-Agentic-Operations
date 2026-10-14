import { useState } from 'react';
import { GitPullRequest, Check, X, Play, Clock, AlertTriangle } from 'lucide-react';
import type { ChangeRequest } from '@/types';

interface Props {
  requests: ChangeRequest[];
  onApprove: (requestId: string) => void;
  onReject: (requestId: string) => void;
  onExecute: (requestId: string) => void;
  loading: boolean;
}

const statusConfig: Record<string, { color: string; bg: string; label: string }> = {
  pending_review: { color: 'text-yellow-400', bg: 'bg-yellow-500/20', label: 'Pending Review' },
  approved: { color: 'text-blue-400', bg: 'bg-blue-500/20', label: 'Approved' },
  rejected: { color: 'text-red-400', bg: 'bg-red-500/20', label: 'Rejected' },
  executing: { color: 'text-purple-400', bg: 'bg-purple-500/20', label: 'Executing' },
  completed: { color: 'text-green-400', bg: 'bg-green-500/20', label: 'Completed' },
  failed: { color: 'text-red-400', bg: 'bg-red-500/20', label: 'Failed' },
  cancelled: { color: 'text-gray-400', bg: 'bg-gray-500/20', label: 'Cancelled' },
  rolled_back: { color: 'text-orange-400', bg: 'bg-orange-500/20', label: 'Rolled Back' },
};

export default function ChangeRequestPanel({ requests, onApprove, onReject, onExecute, loading }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="bg-gray-800 rounded-xl p-5">
      <h3 className="text-sm font-medium text-gray-300 mb-4 flex items-center gap-2">
        <GitPullRequest className="w-4 h-4" /> Change Requests ({requests.length})
      </h3>

      {requests.length === 0 ? (
        <p className="text-sm text-gray-500">No change requests</p>
      ) : (
        <div className="space-y-3">
          {requests.map(cr => {
            const cfg = statusConfig[cr.status] || statusConfig.pending_review;
            const expanded = expandedId === cr.request_id;

            return (
              <div key={cr.request_id} className="bg-gray-700/50 rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedId(expanded ? null : cr.request_id)}
                  className="w-full px-4 py-3 text-left"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-200 truncate">{cr.title}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${cfg.bg} ${cfg.color}`}>{cfg.label}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {cr.change_type} &middot; {cr.device_count} device(s) &middot; {cr.created_at?.split('T')[0] || 'N/A'}
                      </p>
                    </div>
                    {cr.ai_impact_score !== null && cr.ai_impact_score !== undefined && (
                      <div className="flex items-center gap-1 ml-3">
                        <AlertTriangle className={`w-3.5 h-3.5 ${cr.ai_impact_score > 7 ? 'text-red-400' : cr.ai_impact_score > 4 ? 'text-yellow-400' : 'text-green-400'}`} />
                        <span className="text-xs text-gray-400">Risk: {cr.ai_impact_score}/10</span>
                      </div>
                    )}
                  </div>
                </button>

                {expanded && (
                  <div className="px-4 pb-4 border-t border-gray-600/50 pt-3">
                    {cr.description && <p className="text-sm text-gray-400 mb-3">{cr.description}</p>}

                    {/* Target Devices */}
                    <div className="mb-3">
                      <p className="text-xs text-gray-500 mb-1">Target Devices:</p>
                      <div className="flex flex-wrap gap-1">
                        {cr.target_devices.map(d => (
                          <span key={d.device_id} className="text-xs bg-gray-600 text-gray-300 px-2 py-0.5 rounded">
                            {d.hostname} ({d.device_type})
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* AI Assessment */}
                    {cr.ai_risk_assessment && (
                      <div className="mb-3 p-2 bg-gray-600/30 rounded text-xs text-gray-400">
                        <p className="text-gray-500 mb-0.5">AI Assessment:</p>
                        {cr.ai_risk_assessment}
                      </div>
                    )}

                    {/* Execution Log */}
                    {cr.execution_log && cr.execution_log.length > 0 && (
                      <div className="mb-3">
                        <p className="text-xs text-gray-500 mb-1">Execution Log:</p>
                        {cr.execution_log.map((log, i) => (
                          <div key={i} className="text-xs flex items-center gap-2 py-0.5">
                            <span className={log.status === 'applied' ? 'text-green-400' : 'text-red-400'}>
                              {log.status === 'applied' ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                            </span>
                            <span className="text-gray-400">{log.device_id}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Meta */}
                    <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                      {cr.requested_by && <span>Requested by: {cr.requested_by}</span>}
                      {cr.approved_by && <span>Approved by: {cr.approved_by}</span>}
                      {cr.rollback_available && <span className="text-blue-400">Rollback available</span>}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {cr.status === 'pending_review' && (
                        <>
                          <button onClick={() => onApprove(cr.request_id)} disabled={loading}
                            className="px-3 py-1.5 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white text-xs rounded-md flex items-center gap-1">
                            <Check className="w-3 h-3" /> Approve
                          </button>
                          <button onClick={() => onReject(cr.request_id)} disabled={loading}
                            className="px-3 py-1.5 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-xs rounded-md flex items-center gap-1">
                            <X className="w-3 h-3" /> Reject
                          </button>
                        </>
                      )}
                      {cr.status === 'approved' && (
                        <button onClick={() => onExecute(cr.request_id)} disabled={loading}
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs rounded-md flex items-center gap-1">
                          <Play className="w-3 h-3" /> Execute
                        </button>
                      )}
                      {cr.status === 'executing' && (
                        <span className="text-xs text-purple-400 flex items-center gap-1">
                          <Clock className="w-3 h-3 animate-spin" /> Executing...
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
