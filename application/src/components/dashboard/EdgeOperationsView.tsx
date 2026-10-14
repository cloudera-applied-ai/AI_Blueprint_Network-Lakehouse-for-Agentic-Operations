import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Brain,
  CheckCircle,
  Cpu,
  Database,
  HardDrive,
  Loader2,
  MapPin,
  Play,
  Radar,
  Server,
  Terminal,
  Wrench,
} from 'lucide-react';
import { apiRequest } from '@/services/api/baseClient';
import {
  getEdgeEvent,
  getStagingStatus,
  listEdgeEvents,
  listEdgeScenarios,
  pollEdgeStaging,
  triggerEdgeEvent,
} from '@/services/api';
import type { EdgeEvent, EdgeScenario, StagingStatus, ThoughtMessage } from '@/types/edge';

interface HeadendItem {
  headend_id: string;
  name: string;
  region?: string;
  city?: string;
}

interface EdgeOperationsViewProps {
  onOpenCapture?: (captureId: string) => void;
}

const SEV_BADGE: Record<string, string> = {
  low: 'bg-emerald-500/20 text-emerald-300',
  medium: 'bg-amber-500/20 text-amber-300',
  high: 'bg-orange-500/20 text-orange-300',
  critical: 'bg-red-500/20 text-red-300',
};

export default function EdgeOperationsView({ onOpenCapture }: EdgeOperationsViewProps) {
  const [headends, setHeadends] = useState<HeadendItem[]>([]);
  const [scenarios, setScenarios] = useState<EdgeScenario[]>([]);
  const [events, setEvents] = useState<EdgeEvent[]>([]);
  const [staging, setStaging] = useState<StagingStatus | null>(null);

  const [headendId, setHeadendId] = useState<string>('');
  const [scenarioId, setScenarioId] = useState<string>('');
  const [active, setActive] = useState<EdgeEvent | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    Promise.all([
      apiRequest<{ items: HeadendItem[] }>('/headends?limit=100'),
      listEdgeScenarios(),
      listEdgeEvents(),
      getStagingStatus(),
    ])
      .then(([he, sc, ev, st]) => {
        setHeadends(he.items || []);
        setScenarios(sc);
        setEvents(ev);
        setStaging(st);
        if (he.items?.length) setHeadendId((c) => c || he.items[0].headend_id);
        if (sc.length) setScenarioId((c) => c || sc[0].id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load edge data'));
  }, []);

  const loadEvent = useCallback((id: string) => {
    getEdgeEvent(id).then(setActive).catch(() => {});
  }, []);

  // Poll the active event while it's in flight; auto-ingest on 'staged'.
  useEffect(() => {
    if (!active) return;
    const running = !['completed', 'failed'].includes(active.status);
    if (!running) {
      listEdgeEvents().then(setEvents).catch(() => {});
      return;
    }
    pollRef.current = setInterval(() => {
      getEdgeEvent(active.execution_id)
        .then((e) => {
          setActive(e);
          if (e.status === 'staged') void pollEdgeStaging().catch(() => {});
        })
        .catch(() => {});
    }, 1500);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active?.execution_id, active?.status]);

  const trigger = async () => {
    if (!headendId || !scenarioId) return;
    setTriggering(true);
    setError(null);
    try {
      const { execution_id } = await triggerEdgeEvent(headendId, scenarioId);
      loadEvent(execution_id);
      listEdgeEvents().then(setEvents).catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to trigger edge event');
    } finally {
      setTriggering(false);
    }
  };

  const manualPoll = async () => {
    setPolling(true);
    try {
      await pollEdgeStaging();
      if (active) loadEvent(active.execution_id);
      getStagingStatus().then(setStaging).catch(() => {});
    } finally {
      setPolling(false);
    }
  };

  const selectedHeadend = headends.find((h) => h.headend_id === headendId) || null;

  return (
    <div className="space-y-6">
      {/* Flow explainer + staging status */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-gray-400">
          <span className="flex items-center gap-1.5 text-purple-300 font-medium">
            <Cpu className="w-4 h-4" /> Headend local model detects &amp; contains
          </span>
          <ArrowRight className="w-3.5 h-3.5" />
          <span className="flex items-center gap-1.5">
            <Database className="w-4 h-4" /> Suspect pcap staged to{' '}
            {staging?.backend === 's3' ? (
              <span className="text-emerald-300">S3 ({staging.bucket})</span>
            ) : (
              <span className="text-amber-300 inline-flex items-center gap-1">
                <HardDrive className="w-3.5 h-3.5" /> local disk
              </span>
            )}
          </span>
          <ArrowRight className="w-3.5 h-3.5" />
          <span className="flex items-center gap-1.5 text-blue-300">
            <Server className="w-4 h-4" /> Primary DC retrieves &amp; runs the 4 network agents
          </span>
          <span className="ml-auto flex items-center gap-2">
            {staging?.incoming_count ? (
              <span className="text-amber-300">{staging.incoming_count} awaiting ingest</span>
            ) : (
              <span className="text-gray-500">staging idle</span>
            )}
            <button
              onClick={() => void manualPoll()}
              disabled={polling}
              className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded text-xs disabled:opacity-50"
            >
              {polling ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              Poll now
            </button>
          </span>
        </div>
      </div>

      {error && (
        <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg p-3">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-6 min-w-0">
          {/* Trigger controls */}
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Edge data center (headend)</label>
              <select
                value={headendId}
                onChange={(e) => setHeadendId(e.target.value)}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-purple-500"
              >
                {headends.map((h) => (
                  <option key={h.headend_id} value={h.headend_id}>
                    {h.name} — {h.city || h.region || h.headend_id}
                  </option>
                ))}
              </select>
              {selectedHeadend && (
                <p className="flex items-center gap-1 text-[11px] text-gray-500 mt-1">
                  <MapPin className="w-3 h-3" /> Local model: edge-anomaly-detector-v2 (ONNX, 8MB)
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Anomaly scenario</label>
              <div className="grid sm:grid-cols-2 gap-2">
                {scenarios.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setScenarioId(s.id)}
                    className={`text-left rounded-lg border p-3 transition-colors ${
                      scenarioId === s.id
                        ? 'border-purple-500 bg-purple-500/10'
                        : 'border-gray-700 bg-gray-900/40 hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-white">{s.name}</span>
                      <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${SEV_BADGE[s.severity_hint]}`}>
                        {s.severity_hint}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400">{s.description}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => void trigger()}
                disabled={triggering || !headendId || !scenarioId}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                {triggering ? <Loader2 className="w-4 h-4 animate-spin" /> : <Radar className="w-4 h-4" />}
                Trigger edge anomaly
              </button>
            </div>
          </div>

          {active && <ThoughtStream event={active} />}

          {active?.status === 'completed' && active.analysis_id && (
            <button
              onClick={() => onOpenCapture?.(active.analysis_id!)}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
            >
              View the primary-DC analysis of this capture
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Event history */}
        <EdgeEventList events={events} activeId={active?.execution_id ?? null} onSelect={loadEvent} />
      </div>
    </div>
  );
}

function thoughtIcon(type: string) {
  switch (type) {
    case 'thought': return <Brain className="w-3.5 h-3.5" />;
    case 'action': return <Activity className="w-3.5 h-3.5" />;
    case 'observation': return <Activity className="w-3.5 h-3.5" />;
    case 'tool_call': return <Wrench className="w-3.5 h-3.5" />;
    case 'tool_result': return <Terminal className="w-3.5 h-3.5" />;
    case 'final_answer': return <CheckCircle className="w-3.5 h-3.5" />;
    default: return <Activity className="w-3.5 h-3.5" />;
  }
}

function thoughtColor(type: string) {
  switch (type) {
    case 'thought': return 'text-blue-400';
    case 'action': return 'text-amber-400';
    case 'observation': return 'text-cyan-400';
    case 'tool_call': return 'text-purple-400';
    case 'tool_result': return 'text-emerald-400';
    case 'final_answer': return 'text-green-400';
    default: return 'text-slate-400';
  }
}

const STATUS_LABEL: Record<string, string> = {
  running: 'Local model analyzing…',
  edge_complete: 'Detection complete — capturing pcap',
  staged: 'Capture staged — awaiting primary DC',
  analyzing: 'Primary DC analyzing capture…',
  completed: 'Analysis complete',
  failed: 'Failed',
};

function ThoughtStream({ event }: { event: EdgeEvent }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [event.thoughts.length]);
  const running = !['completed', 'failed'].includes(event.status);

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-semibold text-white">
            {event.headend_name || 'Headend'} · local model
          </span>
        </div>
        <span className={`flex items-center gap-1.5 text-xs font-medium ${
          event.status === 'failed' ? 'text-red-400' : running ? 'text-blue-300' : 'text-green-400'
        }`}>
          {running && <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />}
          {STATUS_LABEL[event.status] || event.status}
        </span>
      </div>
      <div className="p-4 space-y-2 max-h-[28rem] overflow-y-auto">
        {event.thoughts.length === 0 && <p className="text-sm text-gray-500">Waiting for the first signal…</p>}
        {event.thoughts.map((t: ThoughtMessage) => (
          <div key={t.id} className="flex items-start gap-3 bg-gray-700/30 rounded-lg p-3">
            <span className={`mt-0.5 flex-shrink-0 ${thoughtColor(t.type)}`}>{thoughtIcon(t.type)}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={`text-[11px] uppercase tracking-wide font-semibold ${thoughtColor(t.type)}`}>
                  {t.type.replace('_', ' ')}
                </span>
                {t.tool_name && <span className="text-[11px] font-mono text-gray-400">{t.tool_name}</span>}
              </div>
              <p className="text-sm text-gray-200 mt-0.5">{t.content}</p>
              {(t.tool_input || t.tool_output) && (
                <div className="mt-1.5 grid sm:grid-cols-2 gap-1.5">
                  {t.tool_input && (
                    <pre className="text-[11px] font-mono text-gray-400 bg-gray-900/60 rounded p-2 overflow-x-auto">
                      → {JSON.stringify(t.tool_input)}
                    </pre>
                  )}
                  {t.tool_output && (
                    <pre className="text-[11px] font-mono text-emerald-300/80 bg-gray-900/60 rounded p-2 overflow-x-auto">
                      ← {JSON.stringify(t.tool_output)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {event.status === 'failed' && event.error && (
          <div className="flex items-start gap-2 text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg p-3">
            <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <span className="whitespace-pre-wrap">{event.error}</span>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}

function EdgeEventList({
  events,
  activeId,
  onSelect,
}: {
  events: EdgeEvent[];
  activeId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 divide-y divide-gray-700/60 self-start">
      <div className="px-4 py-3 flex items-center gap-2 text-sm font-semibold text-white">
        <Radar className="w-4 h-4 text-purple-400" /> Edge events
      </div>
      {events.length === 0 ? (
        <div className="px-4 py-6 text-center text-sm text-gray-500">No edge events yet.</div>
      ) : (
        <ul className="max-h-[32rem] overflow-y-auto divide-y divide-gray-700/60">
          {events.map((e) => {
            const running = !['completed', 'failed'].includes(e.status);
            return (
              <li key={e.execution_id}>
                <button
                  onClick={() => onSelect(e.execution_id)}
                  className={`w-full text-left px-4 py-2.5 hover:bg-gray-700/40 transition-colors ${
                    e.execution_id === activeId ? 'bg-purple-500/10' : ''
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm text-gray-200 font-medium truncate">
                      {e.headend_name || e.headend_id} · {e.scenario_id}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-gray-400">
                      {e.status === 'completed' ? (
                        <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                      ) : e.status === 'failed' ? (
                        <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
                      ) : running ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : null}
                      {e.status}
                    </span>
                  </div>
                  <div className="text-[11px] text-gray-500 mt-1 font-mono">{e.execution_id}</div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
