import { memo, useState, useEffect, useMemo } from 'react';
import {
  Users, Search, RefreshCw, Globe, DollarSign, TrendingUp,
  ChevronDown, ChevronUp, AlertTriangle, CheckCircle2, ThumbsUp, ThumbsDown, Minus
} from 'lucide-react';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell
} from 'recharts';
import {
  getCustomerOverview,
  getCustomerList,
  getSentimentSummary,
  getPlanBreakdown,
  type CustomerOverview,
  type CustomerRecord,
  type SentimentSummary,
  type PlanBreakdown,
} from '@/services/api/customerApi';

const COLORS = ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#6366f1', '#14b8a6'];

const StatusBadge = ({ status }: { status: string }) => {
  const colors: Record<string, string> = {
    active: 'bg-green-900/50 text-green-400',
    suspended: 'bg-yellow-900/50 text-yellow-400',
    closed: 'bg-red-900/50 text-red-400',
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full ${colors[status] || 'bg-gray-700 text-gray-300'}`}>
      {status}
    </span>
  );
};

const SentimentBadge = ({ score }: { score: number | null }) => {
  if (score === null || score === undefined) return <span className="text-gray-500 text-xs">--</span>;
  const color = score > 0.3 ? 'text-green-400' : score > -0.1 ? 'text-yellow-400' : 'text-red-400';
  return <span className={`text-xs font-medium ${color}`}>{score.toFixed(2)}</span>;
};

const CustomerIntelligenceView = memo(() => {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<CustomerOverview | null>(null);
  const [customers, setCustomers] = useState<CustomerRecord[]>([]);
  const [customersTotal, setCustomersTotal] = useState(0);
  const [sentiment, setSentiment] = useState<SentimentSummary | null>(null);
  const [planBreakdown, setPlanBreakdown] = useState<PlanBreakdown | null>(null);
  const [filterRegion, setFilterRegion] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterPlan, setFilterPlan] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [page, setPage] = useState(0);
  const [expandedSection, setExpandedSection] = useState<string | null>('customers');
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const PAGE_SIZE = 50;

  const fetchData = async () => {
    try {
      setLoading(true);
      const [overviewRes, sentimentRes, planRes] = await Promise.all([
        getCustomerOverview(filterRegion || undefined),
        getSentimentSummary(filterRegion || undefined),
        getPlanBreakdown(filterRegion || undefined),
      ]);
      setOverview(overviewRes);
      setSentiment(sentimentRes);
      setPlanBreakdown(planRes);
      setLastRefresh(new Date());
    } catch (error) {
      console.error('Failed to fetch customer data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCustomers = async () => {
    try {
      const res = await getCustomerList({
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
        service_plan: filterPlan || undefined,
        account_status: filterStatus || undefined,
        search: searchQuery || undefined,
        region: filterRegion || undefined,
      });
      setCustomers(res.customers);
      setCustomersTotal(res.total);
    } catch (error) {
      console.error('Failed to fetch customer list:', error);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filterRegion]);

  useEffect(() => {
    fetchCustomers();
  }, [filterRegion, filterPlan, filterStatus, searchQuery, page]);

  // Available plans from overview
  const availablePlans = useMemo(() => {
    if (!overview) return [];
    return Object.keys(overview.by_service_plan).sort();
  }, [overview]);

  // Sentiment by source chart data
  const sentimentBySourceData = useMemo(() => {
    if (!sentiment) return [];
    return sentiment.by_source.map(s => ({
      name: s.source.replace(/_/g, ' '),
      count: s.count,
      score: s.avg_score,
    }));
  }, [sentiment]);

  // Sentiment label distribution for pie chart
  const sentimentLabelData = useMemo(() => {
    if (!sentiment) return [];
    const labelColors: Record<string, string> = {
      positive: '#10b981',
      neutral: '#f59e0b',
      negative: '#ef4444',
      very_negative: '#991b1b',
    };
    return Object.entries(sentiment.by_label).map(([label, count]) => ({
      name: label.replace(/_/g, ' '),
      value: count,
      color: labelColors[label] || '#6b7280',
    }));
  }, [sentiment]);

  // NPS gauge data
  const npsData = useMemo(() => {
    if (!sentiment) return null;
    return sentiment.nps;
  }, [sentiment]);

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  if (loading && !overview) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4" />
          <p className="text-gray-400">Loading Customer Intelligence...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-6 h-6 text-amber-400" />
          <h2 className="text-xl font-bold text-white">Customer Intelligence</h2>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-gray-400" />
            <select
              value={filterRegion}
              onChange={(e) => { setFilterRegion(e.target.value); setPage(0); }}
              className="bg-gray-700 text-gray-200 text-sm rounded px-3 py-1.5 border border-gray-600 focus:outline-none focus:border-blue-500"
            >
              <option value="">All Regions</option>
              {overview && Object.keys(overview.by_service_plan).length > 0 && (
                // We don't have region list here, so skip region options — they're in CoreNetworkView
                <></>
              )}
            </select>
          </div>
          <button
            onClick={() => { fetchData(); fetchCustomers(); }}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 text-gray-200 text-sm rounded hover:bg-gray-600 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <span className="text-xs text-gray-500">Last: {lastRefresh.toLocaleTimeString()}</span>
        </div>
      </div>

      {/* KPI Cards */}
      {overview && (
        <div className="grid grid-cols-5 gap-4">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-400">Total Customers</h3>
              <Users className="w-5 h-5 text-amber-400" />
            </div>
            <p className="text-3xl font-bold text-white">{overview.total_customers.toLocaleString()}</p>
            <p className="text-xs text-gray-500 mt-1">
              {overview.total_active.toLocaleString()} active ({overview.total_customers > 0 ? Math.round((overview.total_active / overview.total_customers) * 100) : 0}%)
            </p>
          </div>

          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-400">Monthly Revenue</h3>
              <DollarSign className="w-5 h-5 text-green-400" />
            </div>
            <p className="text-3xl font-bold text-white">${(overview.total_monthly_revenue / 1000).toFixed(0)}K</p>
            <p className="text-xs text-gray-500 mt-1">
              ${overview.total_active > 0 ? (overview.total_monthly_revenue / overview.total_active).toFixed(2) : '0'}/customer
            </p>
          </div>

          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-400">Avg NPS Score</h3>
              <TrendingUp className="w-5 h-5 text-cyan-400" />
            </div>
            <p className={`text-3xl font-bold ${overview.avg_nps_score >= 7 ? 'text-green-400' : overview.avg_nps_score >= 5 ? 'text-yellow-400' : 'text-red-400'}`}>
              {overview.avg_nps_score.toFixed(1)}
            </p>
            <p className="text-xs text-gray-500 mt-1">{overview.total_sentiments.toLocaleString()} sentiment records</p>
          </div>

          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-400">Avg Sentiment</h3>
              {overview.avg_sentiment_score > 0.1 ? <ThumbsUp className="w-5 h-5 text-green-400" /> :
               overview.avg_sentiment_score > -0.1 ? <Minus className="w-5 h-5 text-yellow-400" /> :
               <ThumbsDown className="w-5 h-5 text-red-400" />}
            </div>
            <p className={`text-3xl font-bold ${overview.avg_sentiment_score > 0.1 ? 'text-green-400' : overview.avg_sentiment_score > -0.1 ? 'text-yellow-400' : 'text-red-400'}`}>
              {overview.avg_sentiment_score.toFixed(3)}
            </p>
            <p className="text-xs text-gray-500 mt-1">Scale: -1.0 to 1.0</p>
          </div>

          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-400">Connection Quality</h3>
              {overview.connection_quality.high_drop_customers > 0 ?
                <AlertTriangle className="w-5 h-5 text-yellow-400" /> :
                <CheckCircle2 className="w-5 h-5 text-green-400" />}
            </div>
            <p className="text-3xl font-bold text-white">
              {overview.total_customers > 0
                ? (100 - (overview.connection_quality.below_speed_threshold / overview.total_customers) * 100).toFixed(1)
                : '0'}%
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {overview.connection_quality.high_drop_customers} high-drop customers
            </p>
          </div>
        </div>
      )}

      {/* Collapsible sections */}
      <div className="space-y-4">
        {/* Customer List */}
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <button
            onClick={() => toggleSection('customers')}
            className="w-full p-4 flex items-center justify-between hover:bg-gray-700/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Users className="w-5 h-5 text-amber-400" />
              <span className="font-medium text-white">Customer Accounts</span>
              <span className="text-sm text-gray-400">({customersTotal.toLocaleString()})</span>
            </div>
            {expandedSection === 'customers' ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
          </button>

          {expandedSection === 'customers' && (
            <div className="px-4 pb-4">
              {/* Filters */}
              <div className="flex items-center gap-3 mb-4">
                <div className="relative flex-1 max-w-xs">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search name or address..."
                    value={searchQuery}
                    onChange={(e) => { setSearchQuery(e.target.value); setPage(0); }}
                    className="w-full pl-9 pr-3 py-1.5 bg-gray-700 text-gray-200 text-sm rounded border border-gray-600 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <select
                  value={filterPlan}
                  onChange={(e) => { setFilterPlan(e.target.value); setPage(0); }}
                  className="bg-gray-700 text-gray-200 text-sm rounded px-3 py-1.5 border border-gray-600"
                >
                  <option value="">All Plans</option>
                  {availablePlans.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <select
                  value={filterStatus}
                  onChange={(e) => { setFilterStatus(e.target.value); setPage(0); }}
                  className="bg-gray-700 text-gray-200 text-sm rounded px-3 py-1.5 border border-gray-600"
                >
                  <option value="">All Statuses</option>
                  <option value="active">Active</option>
                  <option value="suspended">Suspended</option>
                  <option value="closed">Closed</option>
                </select>
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-400 border-b border-gray-700">
                      <th className="pb-2 font-medium">Name</th>
                      <th className="pb-2 font-medium">Location</th>
                      <th className="pb-2 font-medium">Plan</th>
                      <th className="pb-2 font-medium">Modem</th>
                      <th className="pb-2 font-medium">DL Speed</th>
                      <th className="pb-2 font-medium">Drops/24h</th>
                      <th className="pb-2 font-medium">Sentiment</th>
                      <th className="pb-2 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-300">
                    {customers.map(c => {
                      const speedPct = c.provisioned_download_mbps > 0
                        ? (c.actual_download_mbps / c.provisioned_download_mbps) * 100
                        : 0;
                      return (
                        <tr key={c.account_id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                          <td className="py-2">
                            <div className="font-medium text-xs">{c.name}</div>
                            <div className="text-xs text-gray-500">{c.account_id}</div>
                          </td>
                          <td className="py-2 text-xs">{c.city}, {c.state}</td>
                          <td className="py-2 text-xs">{c.service_plan}</td>
                          <td className="py-2 text-xs">{c.modem_manufacturer}<br /><span className="text-gray-500">DOCSIS {c.docsis_version}</span></td>
                          <td className="py-2 text-xs">
                            <span className={speedPct < 80 ? 'text-red-400' : speedPct < 95 ? 'text-yellow-400' : 'text-green-400'}>
                              {c.actual_download_mbps?.toFixed(0) ?? '--'}/{c.provisioned_download_mbps} Mbps
                            </span>
                          </td>
                          <td className={`py-2 text-xs ${c.connection_drops_24h > 5 ? 'text-red-400' : c.connection_drops_24h > 2 ? 'text-yellow-400' : 'text-gray-300'}`}>
                            {c.connection_drops_24h}
                          </td>
                          <td className="py-2"><SentimentBadge score={c.avg_sentiment_score} /></td>
                          <td className="py-2"><StatusBadge status={c.account_status} /></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {customersTotal > PAGE_SIZE && (
                <div className="flex items-center justify-between mt-4 text-sm text-gray-400">
                  <span>Showing {page * PAGE_SIZE + 1}-{Math.min((page + 1) * PAGE_SIZE, customersTotal)} of {customersTotal.toLocaleString()}</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage(Math.max(0, page - 1))}
                      disabled={page === 0}
                      className="px-3 py-1 bg-gray-700 rounded hover:bg-gray-600 disabled:opacity-50"
                    >Prev</button>
                    <button
                      onClick={() => setPage(page + 1)}
                      disabled={(page + 1) * PAGE_SIZE >= customersTotal}
                      className="px-3 py-1 bg-gray-700 rounded hover:bg-gray-600 disabled:opacity-50"
                    >Next</button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sentiment Analytics */}
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <button
            onClick={() => toggleSection('sentiment')}
            className="w-full p-4 flex items-center justify-between hover:bg-gray-700/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
              <span className="font-medium text-white">Sentiment Analytics</span>
              {sentiment && <span className="text-sm text-gray-400">(NPS: {sentiment.nps.score})</span>}
            </div>
            {expandedSection === 'sentiment' ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
          </button>

          {expandedSection === 'sentiment' && sentiment && (
            <div className="px-4 pb-4">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* By Source (bar chart) */}
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
                  <h4 className="text-sm font-medium text-gray-300 mb-3">By Source</h4>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={sentimentBySourceData} layout="vertical" margin={{ left: 5, right: 5, top: 0, bottom: 0 }}>
                        <XAxis type="number" hide />
                        <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 10, fill: '#5B6170' }} />
                        <Tooltip
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const d = payload[0].payload;
                              return (
                                <div className="bg-gray-900 border border-gray-700 px-3 py-2 rounded text-xs">
                                  <p className="text-white font-medium">{d.name}</p>
                                  <p className="text-gray-300">Count: {d.count.toLocaleString()}</p>
                                  <p className="text-gray-300">Avg Score: {d.score.toFixed(3)}</p>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                        <Bar dataKey="count" fill="#06b6d4" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Sentiment Distribution (pie chart) */}
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
                  <h4 className="text-sm font-medium text-gray-300 mb-3">Sentiment Distribution</h4>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={sentimentLabelData}
                          cx="50%" cy="50%"
                          innerRadius={40} outerRadius={70}
                          paddingAngle={2}
                          dataKey="value"
                        >
                          {sentimentLabelData.map((entry, idx) => (
                            <Cell key={idx} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const d = payload[0].payload;
                              return (
                                <div className="bg-gray-900 border border-gray-700 px-3 py-2 rounded text-xs">
                                  <p className="text-white">{d.name}: {d.value.toLocaleString()}</p>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2 justify-center">
                    {sentimentLabelData.map((entry, idx) => (
                      <span key={idx} className="flex items-center gap-1 text-xs text-gray-400">
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                        {entry.name}
                      </span>
                    ))}
                  </div>
                </div>

                {/* NPS Summary */}
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
                  <h4 className="text-sm font-medium text-gray-300 mb-3">Net Promoter Score</h4>
                  {npsData && (
                    <div className="space-y-4">
                      <div className="text-center">
                        <p className={`text-4xl font-bold ${npsData.score > 30 ? 'text-green-400' : npsData.score > 0 ? 'text-yellow-400' : 'text-red-400'}`}>
                          {npsData.score}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">NPS Score</p>
                      </div>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-green-400">Promoters (9-10)</span>
                          <span className="text-green-400">{npsData.promoters}</span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-yellow-400">Passives (7-8)</span>
                          <span className="text-yellow-400">{npsData.passives}</span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-red-400">Detractors (0-6)</span>
                          <span className="text-red-400">{npsData.detractors}</span>
                        </div>
                        <div className="pt-2 border-t border-gray-700 text-xs text-gray-500">
                          Total NPS responses: {npsData.total_responses.toLocaleString()}
                        </div>
                      </div>
                      {/* Resolution status */}
                      <div className="pt-2 border-t border-gray-700">
                        <h5 className="text-xs font-medium text-gray-400 mb-2">Resolution Status</h5>
                        <div className="space-y-1">
                          {Object.entries(sentiment.by_resolution).map(([status, count]) => (
                            <div key={status} className="flex justify-between text-xs">
                              <span className="text-gray-400 capitalize">{status}</span>
                              <span className="text-gray-300">{count.toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Service Plan Breakdown */}
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <button
            onClick={() => toggleSection('plans')}
            className="w-full p-4 flex items-center justify-between hover:bg-gray-700/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <DollarSign className="w-5 h-5 text-green-400" />
              <span className="font-medium text-white">Service Plan Breakdown</span>
              {planBreakdown && <span className="text-sm text-gray-400">({planBreakdown.plans.length} plans)</span>}
            </div>
            {expandedSection === 'plans' ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
          </button>

          {expandedSection === 'plans' && planBreakdown && (
            <div className="px-4 pb-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Plan table */}
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
                  <h4 className="text-sm font-medium text-gray-300 mb-3">Plan Performance</h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-400 border-b border-gray-700">
                          <th className="pb-2 font-medium">Plan</th>
                          <th className="pb-2 font-medium">Customers</th>
                          <th className="pb-2 font-medium">Revenue/mo</th>
                          <th className="pb-2 font-medium">Churn Risk</th>
                          <th className="pb-2 font-medium">Speed Compliance</th>
                        </tr>
                      </thead>
                      <tbody className="text-gray-300">
                        {planBreakdown.plans.map(p => (
                          <tr key={p.plan} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                            <td className="py-2 text-xs font-medium">{p.plan}</td>
                            <td className="py-2 text-xs">{p.total.toLocaleString()}</td>
                            <td className="py-2 text-xs text-green-400">${(p.monthly_revenue / 1000).toFixed(1)}K</td>
                            <td className={`py-2 text-xs ${p.churn_risk_pct > 15 ? 'text-red-400' : p.churn_risk_pct > 8 ? 'text-yellow-400' : 'text-green-400'}`}>
                              {p.churn_risk_pct}%
                            </td>
                            <td className={`py-2 text-xs ${p.speed_compliance_pct < 80 ? 'text-red-400' : p.speed_compliance_pct < 90 ? 'text-yellow-400' : 'text-green-400'}`}>
                              {p.speed_compliance_pct}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Revenue distribution chart */}
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
                  <h4 className="text-sm font-medium text-gray-300 mb-3">Revenue by Plan</h4>
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={planBreakdown.plans} margin={{ left: 5, right: 5, top: 5, bottom: 5 }}>
                        <XAxis dataKey="plan" tick={{ fontSize: 9, fill: '#5B6170' }} angle={-30} textAnchor="end" height={50} />
                        <YAxis tick={{ fontSize: 10, fill: '#5B6170' }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`} />
                        <Tooltip
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const d = payload[0].payload;
                              return (
                                <div className="bg-gray-900 border border-gray-700 px-3 py-2 rounded text-xs">
                                  <p className="text-white font-medium">{d.plan}</p>
                                  <p className="text-green-400">Revenue: ${d.monthly_revenue.toLocaleString()}/mo</p>
                                  <p className="text-gray-300">Customers: {d.total.toLocaleString()}</p>
                                  <p className="text-gray-300">Avg Tenure: {d.avg_tenure_months.toFixed(0)} mo</p>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                        <Bar dataKey="monthly_revenue" radius={[4, 4, 0, 0]}>
                          {planBreakdown.plans.map((_, idx) => (
                            <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Connection Quality (DOCSIS + drop quality from overview) */}
        {overview && (
          <div className="bg-gray-800 rounded-lg border border-gray-700">
            <button
              onClick={() => toggleSection('quality')}
              className="w-full p-4 flex items-center justify-between hover:bg-gray-700/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-green-400" />
                <span className="font-medium text-white">Connection Quality & DOCSIS</span>
              </div>
              {expandedSection === 'quality' ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
            </button>

            {expandedSection === 'quality' && (
              <div className="px-4 pb-4">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* DOCSIS Breakdown */}
                  <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
                    <h4 className="text-sm font-medium text-gray-300 mb-3">DOCSIS Version Distribution</h4>
                    <div className="space-y-2">
                      {Object.entries(overview.by_docsis_version)
                        .sort(([a], [b]) => b.localeCompare(a))
                        .map(([version, count]) => {
                          const pct = overview.total_customers > 0 ? Math.round((count / overview.total_customers) * 100) : 0;
                          return (
                            <div key={version}>
                              <div className="flex justify-between text-xs mb-0.5">
                                <span className="text-gray-400">DOCSIS {version}</span>
                                <span className="text-gray-300">{count.toLocaleString()} ({pct}%)</span>
                              </div>
                              <div className="w-full bg-gray-700 rounded-full h-1.5">
                                <div className="bg-cyan-500 rounded-full h-1.5" style={{ width: `${pct}%` }} />
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>

                  {/* Connection quality summary */}
                  <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
                    <h4 className="text-sm font-medium text-gray-300 mb-3">Speed & Connection Quality</h4>
                    <div className="space-y-3">
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-gray-400">Meeting Speed (80%+ provisioned)</span>
                          <span className="text-green-400">{overview.connection_quality.meeting_speed_threshold.toLocaleString()}</span>
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-gray-400">Below Speed Threshold</span>
                          <span className="text-yellow-400">{overview.connection_quality.below_speed_threshold.toLocaleString()}</span>
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-gray-400">High Drop Rate (&gt;5/day)</span>
                          <span className="text-red-400">{overview.connection_quality.high_drop_customers.toLocaleString()}</span>
                        </div>
                      </div>
                      {overview.total_active > 0 && (
                        <div className="pt-2 border-t border-gray-700">
                          <div className="flex justify-between text-xs">
                            <span className="text-gray-500">Overall Health</span>
                            <span className={
                              overview.connection_quality.below_speed_threshold / overview.total_active > 0.1
                                ? 'text-yellow-400' : 'text-green-400'
                            }>
                              {(100 - (overview.connection_quality.below_speed_threshold / overview.total_active) * 100).toFixed(1)}% healthy
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
});

CustomerIntelligenceView.displayName = 'CustomerIntelligenceView';

export default CustomerIntelligenceView;
