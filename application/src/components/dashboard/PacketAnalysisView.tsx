import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertCircle,
  Bot,
  Bug,
  Cpu,
  Download,
  FileText,
  FileType2,
  Loader2,
  Radar,
  Send,
  Shield,
  ShieldAlert,
  Upload,
  User,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  analyzePcap,
  downloadPcapDocx,
  generatePcapReport,
  getCapture,
  listCaptures,
  pcapChat,
} from '@/services/api';
import type { CaptureResponse, CaptureSummary, FlowInfo, PcapAgentResponse, PcapChatMessage, PcapSeverity } from '@/types/packet';

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

const FLOW_STATE_BADGE: Record<string, string> = {
  established: 'bg-emerald-500/20 text-emerald-300',
  closed: 'bg-gray-600/40 text-gray-300',
  reset: 'bg-red-500/20 text-red-300',
  rejected: 'bg-amber-500/20 text-amber-300',
  syn_sent: 'bg-amber-500/20 text-amber-300',
};

const SEV_COLOR: Record<PcapSeverity, string> = {
  low: 'text-emerald-400',
  medium: 'text-amber-400',
  high: 'text-orange-400',
  critical: 'text-red-400',
};
const SEV_BADGE: Record<PcapSeverity, string> = {
  low: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  medium: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  high: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  critical: 'bg-red-500/20 text-red-300 border-red-500/30',
};
const CHART_COLORS = ['#5555F9', '#FF550C', '#26177B', '#8789FB', '#FE8756', '#100045', '#A8AFB9'];

interface PacketAnalysisViewProps {
  captureId?: string | null;
}

export default function PacketAnalysisView({ captureId }: PacketAnalysisViewProps) {
  const [data, setData] = useState<CaptureResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'agents' | 'overview' | 'flows' | 'threat' | 'report' | 'chat'>('agents');
  const [recent, setRecent] = useState<CaptureSummary[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const refreshRecent = useCallback(() => {
    listCaptures().then(setRecent).catch(() => {});
  }, []);
  useEffect(() => refreshRecent(), [refreshRecent]);

  // Deep-link: load an edge-produced (or picked) capture by id.
  useEffect(() => {
    if (!captureId || captureId === data?.capture_id) return;
    getCapture(captureId)
      .then((c) => {
        setData(c);
        setTab('agents');
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load capture'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [captureId]);

  const handleFile = async (file: File) => {
    setBusy(true);
    setError(null);
    try {
      const c = await analyzePcap(file);
      setData(c);
      setTab('agents');
      refreshRecent();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setBusy(false);
    }
  };

  const stats = useMemo(() => computeStats(data), [data]);

  return (
    <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
      {/* Left: upload + recent */}
      <aside className="lg:sticky lg:top-6 lg:self-start space-y-4">
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files?.[0];
            if (f) void handleFile(f);
          }}
          className="bg-gray-800 rounded-lg border-2 border-dashed border-gray-600 p-6 text-center"
        >
          <Upload className="w-8 h-8 text-gray-500 mx-auto mb-2" />
          <p className="text-sm text-gray-300 font-medium">Drop a .pcap file</p>
          <p className="text-xs text-gray-500 mt-1">or</p>
          <button
            onClick={() => fileRef.current?.click()}
            disabled={busy}
            className="mt-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-sm disabled:opacity-50 inline-flex items-center gap-2"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            {busy ? 'Analyzing…' : 'Browse'}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".pcap,.pcapng,.cap"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void handleFile(f);
            }}
          />
        </div>

        {recent.length > 0 && (
          <div className="bg-gray-800 rounded-lg border border-gray-700">
            <div className="px-4 py-3 text-sm font-semibold text-white">Recent analyses</div>
            <ul className="border-t border-gray-700 max-h-72 overflow-y-auto divide-y divide-gray-700/60">
              {recent.map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => getCapture(c.id).then(setData).catch(() => {})}
                    className={`w-full text-left px-4 py-2 hover:bg-gray-700/50 ${
                      c.id === data?.capture_id ? 'bg-blue-500/10' : ''
                    }`}
                  >
                    <div className="flex items-center gap-2 text-xs text-gray-200">
                      {c.source === 'edge' ? (
                        <Radar className="w-3.5 h-3.5 text-purple-400 flex-shrink-0" />
                      ) : (
                        <Upload className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                      )}
                      <span className="truncate">{c.filename || c.id.slice(0, 10)}</span>
                    </div>
                    <div className="text-[11px] text-gray-500 mt-0.5">
                      {c.total_packets.toLocaleString()} pkts ·{' '}
                      <span className={SEV_COLOR[c.highest_severity]}>{c.highest_severity}</span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/40 rounded-lg p-3 text-xs text-red-200 whitespace-pre-wrap">
            {error}
          </div>
        )}
      </aside>

      {/* Right: results */}
      <div className="space-y-6 min-w-0">
        {data?.edge_context && <EdgeContextBanner ctx={data.edge_context} />}

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {stats.map((s) => (
            <div key={s.label} className="bg-gray-800 rounded-lg border border-gray-700 p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <s.icon className={`w-4 h-4 ${s.color}`} />
                <span className="text-xs text-gray-400">{s.label}</span>
              </div>
              <p className="text-2xl font-bold text-white tabular-nums">{s.value}</p>
            </div>
          ))}
        </div>

        {!data ? (
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-12 text-center">
            <Shield className="w-10 h-10 text-gray-500 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-white mb-1">No capture loaded</h3>
            <p className="text-sm text-gray-400">
              Upload a PCAP, or trigger an edge anomaly in Edge Operations to analyze a staged capture.
            </p>
          </div>
        ) : (
          <>
            <div className="flex gap-2 border-b border-gray-700">
              {(['agents', 'overview', 'flows', 'threat', 'report', 'chat'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-4 py-2 text-sm font-medium capitalize border-b-2 -mb-px transition-colors ${
                    tab === t
                      ? 'border-blue-500 text-white'
                      : 'border-transparent text-gray-400 hover:text-white'
                  }`}
                >
                  {t === 'agents' ? 'Agent Analysis' : t === 'threat' ? 'Threat Intel' : t === 'flows' ? 'Flows & DNS' : t}
                </button>
              ))}
            </div>

            {tab === 'agents' && <AgentPanel agents={data.agents} />}
            {tab === 'overview' && <OverviewPanel data={data} />}
            {tab === 'flows' && <FlowsPanel data={data} />}
            {tab === 'threat' && <ThreatPanel data={data} />}
            {tab === 'report' && <ReportPanel captureId={data.capture_id} />}
            {tab === 'chat' && <ChatPanel captureId={data.capture_id} />}
          </>
        )}
      </div>
    </div>
  );
}

function computeStats(data: CaptureResponse | null) {
  if (!data) {
    return [
      { label: 'Packets', value: '—', icon: Activity, color: 'text-blue-400' },
      { label: 'External IPs', value: '—', icon: Shield, color: 'text-gray-400' },
      { label: 'Blocklist hits', value: '—', icon: ShieldAlert, color: 'text-gray-400' },
      { label: 'Highest severity', value: '—', icon: AlertCircle, color: 'text-gray-400' },
    ];
  }
  const m = data.metadata;
  const order: PcapSeverity[] = ['low', 'medium', 'high', 'critical'];
  const highest = data.agents.reduce<PcapSeverity>(
    (acc, a) => (order.indexOf(a.severity) > order.indexOf(acc) ? a.severity : acc),
    'low'
  );
  const blocklist = Object.values(m.ip_reputations || {}).filter((r) => r.in_blocklist).length;
  return [
    { label: 'Packets', value: m.total_packets.toLocaleString(), icon: Activity, color: 'text-blue-400' },
    { label: 'External IPs', value: String(Object.keys(m.geo_locations || {}).length), icon: Shield, color: 'text-emerald-400' },
    { label: 'Blocklist hits', value: String(blocklist), icon: ShieldAlert, color: blocklist ? 'text-red-400' : 'text-gray-400' },
    { label: 'Highest severity', value: highest.toUpperCase(), icon: AlertCircle, color: SEV_COLOR[highest] },
  ];
}

function AgentPanel({ agents }: { agents: PcapAgentResponse[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {agents.map((a) => (
        <div key={a.agent_name} className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-purple-400" />
              <h3 className="text-sm font-semibold text-white">{a.agent_name}</h3>
            </div>
            <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border ${SEV_BADGE[a.severity]}`}>
              {a.severity}
            </span>
          </div>
          <p className="text-xs text-gray-300 whitespace-pre-wrap max-h-48 overflow-y-auto">{a.analysis}</p>
          {a.findings.length > 0 && (
            <div className="mt-3 space-y-1">
              {a.findings.slice(0, 6).map((f, i) => (
                <div key={i} className="text-[11px] text-gray-400">
                  <span className="font-semibold text-gray-200">{f.type}:</span> {f.description}
                </div>
              ))}
            </div>
          )}
          {a.recommendations.length > 0 && (
            <ul className="mt-3 list-disc list-inside text-[11px] text-gray-400 space-y-0.5">
              {a.recommendations.slice(0, 4).map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

function OverviewPanel({ data }: { data: CaptureResponse }) {
  const protoData = Object.entries(data.metadata.protocols).map(([name, value]) => ({ name, value }));
  const connData = data.metadata.top_connections.slice(0, 8).map((c) => ({
    name: `${c.source_ip.slice(-6)}→${c.dest_ip.slice(-6)}`,
    packets: c.packet_count,
  }));
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-white mb-3">Protocol distribution</h3>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={protoData} dataKey="value" nameKey="name" outerRadius={80} label>
              {protoData.map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-white mb-3">Top connections (packets)</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={connData}>
            <XAxis dataKey="name" tick={{ fill: '#5B6170', fontSize: 10 }} interval={0} angle={-30} textAnchor="end" height={60} />
            <YAxis tick={{ fill: '#5B6170', fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey="packets" fill="#5555F9" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function FlowsPanel({ data }: { data: CaptureResponse }) {
  const m = data.metadata;
  const flows: FlowInfo[] = m.flows || [];
  const dns = m.dns_queries || [];
  const tls = m.tls_handshakes || [];
  const l2 = m.l2_summary || {};
  const suspicious = (f: FlowInfo) =>
    f.state === 'reset' || f.state === 'rejected' ||
    (f.bytes_out > 4 * (f.bytes_in + 1) && f.bytes_out > 50_000);

  return (
    <div className="space-y-4">
      {Object.keys(l2).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(l2).map(([k, v]) => (
            <span key={k} className="text-[11px] px-2 py-1 rounded bg-gray-800 border border-gray-700 text-gray-300">
              {k}: <span className="font-semibold text-white">{v.toLocaleString()}</span>
            </span>
          ))}
        </div>
      )}

      {/* Flow table */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-white mb-3">Transport flows ({flows.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500 text-left border-b border-gray-700">
                <th className="py-1.5 pr-3 font-medium">Source</th>
                <th className="py-1.5 pr-3 font-medium">Destination</th>
                <th className="py-1.5 pr-3 font-medium">Service</th>
                <th className="py-1.5 pr-3 font-medium">State</th>
                <th className="py-1.5 pr-3 font-medium text-right">Out</th>
                <th className="py-1.5 pr-3 font-medium text-right">In</th>
                <th className="py-1.5 pr-3 font-medium text-right">Dur</th>
                <th className="py-1.5 pr-3 font-medium">SNI / flags</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {flows.slice(0, 60).map((f, i) => (
                <tr key={i} className={`border-b border-gray-700/50 ${suspicious(f) ? 'bg-red-500/5' : ''}`}>
                  <td className="py-1 pr-3 text-gray-300 whitespace-nowrap">{f.source_ip}:{f.source_port}</td>
                  <td className="py-1 pr-3 text-gray-300 whitespace-nowrap">{f.dest_ip}:{f.dest_port}</td>
                  <td className="py-1 pr-3 text-gray-400">{f.service || f.protocol}</td>
                  <td className="py-1 pr-3">
                    {f.state && (
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${FLOW_STATE_BADGE[f.state] || 'bg-gray-600/40 text-gray-300'}`}>
                        {f.state}
                      </span>
                    )}
                  </td>
                  <td className="py-1 pr-3 text-right text-gray-300 tabular-nums">{fmtBytes(f.bytes_out)}</td>
                  <td className="py-1 pr-3 text-right text-gray-300 tabular-nums">{fmtBytes(f.bytes_in)}</td>
                  <td className="py-1 pr-3 text-right text-gray-500 tabular-nums">{f.duration_s ? `${f.duration_s.toFixed(1)}s` : '—'}</td>
                  <td className="py-1 pr-3 text-gray-400 max-w-[220px] truncate">
                    {f.sni || (f.tcp_flags.length ? f.tcp_flags.join(' ') : '')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* DNS */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-white mb-3">DNS queries ({dns.length})</h3>
          {dns.length === 0 ? (
            <p className="text-xs text-gray-500">No DNS in this capture.</p>
          ) : (
            <ul className="text-xs space-y-1 max-h-72 overflow-y-auto font-mono">
              {dns.slice(0, 40).map((q, i) => (
                <li key={i} className="flex items-baseline gap-2">
                  <span className={q.nxdomain ? 'text-amber-300' : 'text-gray-300'}>{q.qname}</span>
                  <span className="text-gray-600">{q.qtype}</span>
                  {q.nxdomain && <span className="text-amber-400 text-[10px]">NXDOMAIN</span>}
                  {q.response_ips.length > 0 && (
                    <span className="text-gray-500 truncate">→ {q.response_ips.join(', ')}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* TLS */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-white mb-3">TLS handshakes ({tls.length})</h3>
          {tls.length === 0 ? (
            <p className="text-xs text-gray-500">No TLS handshakes in this capture.</p>
          ) : (
            <ul className="text-xs space-y-1.5 max-h-72 overflow-y-auto font-mono">
              {tls.slice(0, 40).map((t, i) => (
                <li key={i}>
                  <div className="text-gray-300 truncate">{t.sni || <span className="text-gray-500 italic">(no SNI)</span>}</div>
                  <div className="text-[11px] text-gray-500">
                    {t.version} · JA3 {t.ja3_hash.slice(0, 12)}…
                    {t.alpn.length > 0 && <span> · {t.alpn.join(',')}</span>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function ThreatPanel({ data }: { data: CaptureResponse }) {
  const reps = Object.values(data.metadata.ip_reputations || {}).filter((r) => r.in_blocklist);
  const cves = data.metadata.cve_candidates || [];
  return (
    <div className="space-y-4">
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-red-400" /> Blocklisted IPs ({reps.length})
        </h3>
        {reps.length === 0 ? (
          <p className="text-xs text-gray-500">No IPs in this capture matched the configured blocklists.</p>
        ) : (
          <ul className="text-xs text-gray-300 space-y-1">
            {reps.map((r) => (
              <li key={r.ip}>
                <span className="font-mono">{r.ip}</span> — {r.sources.join(', ')} · {r.categories.join(', ')}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
          <Bug className="w-4 h-4 text-purple-400" /> CVE candidates ({cves.length})
        </h3>
        {cves.length === 0 ? (
          <p className="text-xs text-gray-500">No CVE candidates derived from this capture.</p>
        ) : (
          <ul className="text-xs text-gray-300 space-y-1">
            {cves.map((c) => (
              <li key={c.id}>
                <a href={c.url} target="_blank" rel="noreferrer" className="text-blue-400 font-mono">{c.id}</a>
                {c.severity && <span className="ml-1 text-gray-500">({c.severity})</span>} — {c.summary}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function ReportPanel({ captureId }: { captureId: string }) {
  const [report, setReport] = useState('');
  const [busy, setBusy] = useState(false);
  const [docxBusy, setDocxBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setBusy(true);
    setError(null);
    try {
      const { report_markdown } = await generatePcapReport(captureId);
      setReport(report_markdown);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Report failed');
    } finally {
      setBusy(false);
    }
  };
  const docx = async () => {
    setDocxBusy(true);
    setError(null);
    try {
      await downloadPcapDocx(captureId);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Word export failed');
    } finally {
      setDocxBusy(false);
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-400" /> Security report
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => void generate()}
            disabled={busy}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm disabled:opacity-50 inline-flex items-center gap-1.5"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
            {report ? 'Regenerate' : 'Generate'}
          </button>
          {report && (
            <button
              onClick={() => {
                const blob = new Blob([report], { type: 'text/markdown' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `pcap-report-${new Date().toISOString().split('T')[0]}.md`;
                a.click();
                URL.revokeObjectURL(url);
              }}
              className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded text-sm inline-flex items-center gap-1.5"
            >
              <Download className="w-4 h-4" /> Markdown
            </button>
          )}
          <button
            onClick={() => void docx()}
            disabled={docxBusy}
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded text-sm disabled:opacity-50 inline-flex items-center gap-1.5"
          >
            {docxBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileType2 className="w-4 h-4" />}
            Word (.docx)
          </button>
        </div>
      </div>
      {error && <div className="text-xs text-red-400 mb-2">{error}</div>}
      {report ? (
        <pre className="text-xs text-gray-300 whitespace-pre-wrap max-h-[60vh] overflow-y-auto font-sans bg-gray-900/50 rounded p-4">
          {report}
        </pre>
      ) : (
        <p className="text-sm text-gray-400">
          Generates an executive summary, severity assessment, per-agent findings, timeline, and
          recommendations. Export as Markdown or a formatted Word document.
        </p>
      )}
    </div>
  );
}

function ChatPanel({ captureId }: { captureId: string }) {
  const [messages, setMessages] = useState<PcapChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [docxBusy, setDocxBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages, busy]);

  const send = async (text: string) => {
    const t = text.trim();
    if (!t) return;
    const next: PcapChatMessage[] = [...messages, { role: 'user', content: t }];
    setMessages(next);
    setInput('');
    setBusy(true);
    try {
      const { reply } = await pcapChat(captureId, next);
      setMessages([...next, { role: 'assistant', content: reply }]);
    } catch (e) {
      setMessages([...next, { role: 'assistant', content: `Error: ${e instanceof Error ? e.message : 'chat failed'}` }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 flex flex-col" style={{ height: 'calc(100vh - 360px)' }}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <span className="text-sm font-semibold text-white flex items-center gap-2">
          <Bot className="w-4 h-4 text-purple-400" /> Operator assistant
        </span>
        <button
          onClick={async () => {
            setDocxBusy(true);
            try {
              await downloadPcapDocx(captureId, { includeChat: true, messages });
            } finally {
              setDocxBusy(false);
            }
          }}
          disabled={docxBusy}
          className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded text-xs disabled:opacity-50"
        >
          {docxBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileType2 className="w-3.5 h-3.5" />}
          Export Word report
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-center text-gray-500 text-sm py-8">Ask about this capture — threats, hosts, exfiltration.</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role !== 'user' && <Bot className="w-6 h-6 text-purple-400 flex-shrink-0" />}
            <div className={`max-w-[75%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
              m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-100'
            }`}>
              {m.content}
            </div>
            {m.role === 'user' && <User className="w-6 h-6 text-blue-400 flex-shrink-0" />}
          </div>
        ))}
        {busy && <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />}
        <div ref={endRef} />
      </div>
      <div className="p-3 border-t border-gray-700 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void send(input)}
          placeholder="Ask a question…"
          disabled={busy}
          className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg text-sm focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        <button
          onClick={() => void send(input)}
          disabled={busy || !input.trim()}
          className="p-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg disabled:opacity-50"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}

function EdgeContextBanner({ ctx }: { ctx: NonNullable<CaptureResponse['edge_context']> }) {
  return (
    <div className="bg-purple-500/10 border border-purple-500/40 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <Radar className="w-5 h-5 text-purple-300 mt-0.5" />
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-purple-200">
            Edge-ingested capture — {ctx.headend_name || ctx.headend_id}
          </h3>
          <p className="text-xs text-purple-200/70 mt-0.5">
            Scenario <span className="font-mono">{ctx.scenario_id}</span> detected and contained by the
            headend's local model, then staged ({ctx.staging_backend}) for deep analysis.
          </p>
          {ctx.edge_actions?.length > 0 && (
            <ul className="mt-2 grid sm:grid-cols-2 gap-1">
              {ctx.edge_actions.map((a, i) => (
                <li key={i} className="text-[11px] text-purple-100/80">
                  <span className="font-semibold">{a.action}</span>{' '}
                  <span className="font-mono text-purple-200/70">{a.target}</span> — {a.detail}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
