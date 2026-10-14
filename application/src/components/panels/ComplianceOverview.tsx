import { Shield, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';
import type { ComplianceSummary } from '@/types';

interface Props {
  summary: ComplianceSummary | null;
  onScan: () => void;
  scanning: boolean;
}

const typeLabels: Record<string, string> = {
  firewall: 'Firewalls',
  switch: 'Switches',
  router: 'Routers',
  modem: 'Modems',
};

export default function ComplianceOverview({ summary, onScan, scanning }: Props) {
  if (!summary) {
    return (
      <div className="bg-gray-800 rounded-xl p-5">
        <p className="text-gray-500 text-sm">Loading compliance data...</p>
      </div>
    );
  }

  const rate = summary.overall_compliance_rate;
  const rateColor = rate >= 90 ? 'text-green-400' : rate >= 70 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="bg-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <Shield className="w-4 h-4" /> Compliance Dashboard
        </h3>
        <button
          onClick={onScan}
          disabled={scanning}
          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs rounded-md flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${scanning ? 'animate-spin' : ''}`} />
          {scanning ? 'Scanning...' : 'Run Scan'}
        </button>
      </div>

      {/* Overall Rate */}
      <div className="flex items-center gap-4 mb-5">
        <div className="relative w-20 h-20">
          <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none" stroke="#E6E7EF" strokeWidth="3" />
            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none" stroke={rate >= 90 ? '#22c55e' : rate >= 70 ? '#eab308' : '#ef4444'}
              strokeWidth="3" strokeDasharray={`${rate}, 100`} strokeLinecap="round" />
          </svg>
          <span className={`absolute inset-0 flex items-center justify-center text-lg font-bold ${rateColor}`}>
            {rate}%
          </span>
        </div>
        <div>
          <p className={`text-2xl font-bold ${rateColor}`}>{rate}%</p>
          <p className="text-xs text-gray-500">Overall Compliance</p>
        </div>
        <div className="flex-1 grid grid-cols-3 gap-2 ml-4">
          <StatBadge icon={<CheckCircle className="w-3.5 h-3.5 text-green-400" />} label="Compliant" value={summary.totals.compliant || 0} />
          <StatBadge icon={<AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />} label="Drifted" value={summary.totals.drifted || 0} />
          <StatBadge icon={<AlertTriangle className="w-3.5 h-3.5 text-red-400" />} label="Non-Compliant" value={summary.totals.non_compliant || 0} />
        </div>
      </div>

      {/* By Device Type */}
      <div className="space-y-2">
        {Object.entries(summary.by_device_type).map(([type, data]) => {
          const typeRate = data.total > 0 ? Math.round((data.compliant / data.total) * 100) : 100;
          return (
            <div key={type} className="bg-gray-700/50 rounded-lg p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-300">{typeLabels[type] || type}</span>
                <span className="text-xs text-gray-500">{data.total} devices</span>
              </div>
              <div className="w-full bg-gray-600 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${typeRate >= 90 ? 'bg-green-500' : typeRate >= 70 ? 'bg-yellow-500' : 'bg-red-500'}`}
                  style={{ width: `${typeRate}%` }}
                />
              </div>
              <div className="flex justify-between mt-1 text-xs text-gray-500">
                <span>{data.compliant} compliant</span>
                {data.drifted > 0 && <span className="text-yellow-400">{data.drifted} drifted</span>}
                {data.non_compliant > 0 && <span className="text-red-400">{data.non_compliant} non-compliant</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatBadge({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="bg-gray-700/50 rounded-lg p-2 text-center">
      <div className="flex items-center justify-center gap-1 mb-0.5">{icon}<span className="text-lg font-bold text-white">{value}</span></div>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}
