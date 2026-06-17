import React, { useMemo } from 'react';
import { useReviewStore } from '../store/reviewStore';
import { computeAnalytics } from '../utils/dataUtils';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Legend,
} from 'recharts';
import {
  TrendingUp,
  CheckCircle2,
  XCircle,
  SkipForward,
  Clock,
  BarChart2,
  Globe,
  Mic,
  User,
  LayoutGrid,
} from 'lucide-react';

const PALETTE = [
  '#6366f1', '#818cf8', '#a5b4fc', '#c7d2fe',
  '#22c55e', '#4ade80', '#86efac',
  '#f59e0b', '#fbbf24', '#fde68a',
  '#ef4444', '#f87171', '#fca5a5',
  '#06b6d4', '#22d3ee', '#67e8f9',
];

const TOOLTIP_STYLE = {
  backgroundColor: '#ffffff',
  border: '1px solid #e2e8f0',
  borderRadius: '8px',
  fontSize: '11px',
  color: '#1e293b',
};

function StatCard({
  label,
  value,
  sub,
  icon,
  color,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ReactNode;
  color: string;
}) {
  return (
    <div className="bg-surface-800/40 border border-surface-700/30 rounded-xl p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[11px] text-surface-400 font-medium">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
          {sub && <p className="text-[10px] text-surface-500 mt-0.5">{sub}</p>}
        </div>
        <div className={`${color} opacity-60`}>{icon}</div>
      </div>
    </div>
  );
}

function SectionHeader({ title, icon }: { title: string; icon: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="text-accent-400">{icon}</span>
      <h2 className="text-sm font-semibold text-surface-100">{title}</h2>
    </div>
  );
}

function ChartCard({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-surface-800/40 border border-surface-700/30 rounded-xl p-4">
      <SectionHeader title={title} icon={icon} />
      {children}
    </div>
  );
}

function formatDuration(sec: number) {
  if (sec == null || isNaN(sec)) return '0s';
  if (sec < 60) return `${sec.toFixed(1)}s`;
  const mins = sec / 60;
  if (mins < 60) return `${mins.toFixed(1)}m`;
  const hrs = mins / 60;
  return `${hrs.toFixed(2)}h`;
}

export function AnalyticsDashboard() {
  const items = useReviewStore((s) => s.items);
  const analytics = useMemo(() => computeAnalytics(items), [items]);

  if (items.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-surface-500">
        <p>No data loaded. Import a dataset to see analytics.</p>
      </div>
    );
  }

  const a = analytics;

  // Prepare pie data
  const statusPie = [
    { name: 'Accepted', value: a.approved, color: '#22c55e' },
    { name: 'Rejected', value: a.rejected, color: '#ef4444' },
    { name: 'Skipped', value: a.skipped, color: '#f59e0b' },
    { name: 'Unreviewed', value: a.remaining, color: '#4a4e6b' },
  ].filter((d) => d.value > 0);

  const rejectionData = Object.entries(a.rejectionReasonCounts)
    .sort((x, y) => y[1] - x[1])
    .map(([name, count]) => ({ name: name.replace(/_/g, ' '), count }));

  const errorCatData = Object.entries(a.errorCategoryCounts)
    .sort((x, y) => y[1] - x[1])
    .map(([name, count]) => ({ name: name.replace(/_/g, ' '), count }));

  const languageData = Object.entries(a.languageDist)
    .sort((x, y) => y[1] - x[1])
    .map(([name, count]) => ({ name, count }));

  const acceptedDurationLanguageData = Object.entries(a.acceptedDurationPerLanguage || {})
    .sort((x, y) => y[1] - x[1])
    .map(([name, duration]) => ({
      name,
      duration: parseFloat((duration / 60).toFixed(2)), // show in minutes
    }));

  const emotionData = Object.entries(a.emotionDist)
    .sort((x, y) => y[1] - x[1])
    .map(([name, count]) => ({ name, count }));

  const channelData = Object.entries(a.channelDist)
    .sort((x, y) => y[1] - x[1])
    .map(([name, count]) => ({ name, count }));

  return (
    <div className="min-h-screen bg-surface-950 text-surface-100 p-6 overflow-auto">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-surface-50 flex items-center gap-2">
              <BarChart2 size={20} className="text-accent-400" />
              Review Analytics
            </h1>
            <p className="text-surface-400 text-xs mt-0.5">Live metrics from your review session</p>
          </div>
        </div>

        {/* Key stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          <StatCard label="Total" value={a.total} icon={<LayoutGrid size={20} />} color="text-surface-200" />
          <StatCard label="Reviewed" value={a.reviewed} sub={`${((a.reviewed / a.total) * 100).toFixed(0)}%`} icon={<TrendingUp size={20} />} color="text-accent-400" />
          <StatCard label="Accepted" value={a.approved} icon={<CheckCircle2 size={20} />} color="text-success-400" />
          <StatCard label="Rejected" value={a.rejected} icon={<XCircle size={20} />} color="text-danger-400" />
          <StatCard label="Skipped" value={a.skipped} icon={<SkipForward size={20} />} color="text-warning-400" />
          <StatCard label="Remaining" value={a.remaining} icon={<Clock size={20} />} color="text-surface-400" />
          <StatCard label="Approval" value={`${a.approvalRate.toFixed(1)}%`} icon={<TrendingUp size={20} />} color="text-success-300" />
          <StatCard label="Accepted Duration" value={formatDuration(a.totalAcceptedDuration)} icon={<Clock size={20} />} color="text-success-400 font-mono" />
        </div>

        {/* Score stats */}
        <div className="grid grid-cols-3 gap-3">
          <StatCard
            label="Avg Transcript Score"
            value={a.avgTranscriptScore > 0 ? a.avgTranscriptScore.toFixed(2) : '–'}
            sub="out of 5.0"
            icon={<Mic size={20} />}
            color="text-accent-300"
          />
          <StatCard
            label="Avg Audio Score"
            value={a.avgAudioScore > 0 ? a.avgAudioScore.toFixed(2) : '–'}
            sub="out of 5.0"
            icon={<BarChart2 size={20} />}
            color="text-accent-300"
          />
          <StatCard
            label="Correction Rate"
            value={`${a.correctionRate.toFixed(1)}%`}
            sub="transcripts modified"
            icon={<TrendingUp size={20} />}
            color="text-warning-300"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

          {/* Review status pie */}
          <ChartCard title="Review Status Distribution" icon={<CheckCircle2 size={14} />}>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusPie}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                    labelLine={false}
                    fontSize={10}
                  >
                    {statusPie.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          {/* Duration distribution */}
          <ChartCard title="Duration Distribution" icon={<Clock size={14} />}>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={a.durationBuckets} barSize={28}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2e3150" />
                  <XAxis dataKey="range" tick={{ fontSize: 10, fill: '#6c7193' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#6c7193' }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          {/* Language distribution */}
          <ChartCard title="Language Distribution (Segment Count)" icon={<Globe size={14} />}>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={languageData} layout="vertical" barSize={16}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2e3150" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10, fill: '#6c7193' }} />
                  <YAxis dataKey="name" type="category" width={60} tick={{ fontSize: 10, fill: '#6c7193' }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {languageData.map((_, i) => (
                      <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          {/* Accepted Duration per Language */}
          <ChartCard title="Accepted Duration per Language (Minutes)" icon={<Clock size={14} />}>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={acceptedDurationLanguageData} layout="vertical" barSize={16}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2e3150" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10, fill: '#6c7193' }} />
                  <YAxis dataKey="name" type="category" width={60} tick={{ fontSize: 10, fill: '#6c7193' }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value) => [`${value} mins`, 'Duration']} />
                  <Bar dataKey="duration" radius={[0, 4, 4, 0]}>
                    {acceptedDurationLanguageData.map((_, i) => (
                      <Cell key={i} fill={PALETTE[(i + 2) % PALETTE.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          {/* Emotion distribution */}
          <ChartCard title="Emotion / Style Distribution" icon={<Mic size={14} />}>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={emotionData} layout="vertical" barSize={14}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2e3150" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10, fill: '#6c7193' }} />
                  <YAxis dataKey="name" type="category" width={80} tick={{ fontSize: 10, fill: '#6c7193' }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {emotionData.map((_, i) => (
                      <Cell key={i} fill={PALETTE[(i + 4) % PALETTE.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          {/* Rejection reasons */}
          {rejectionData.length > 0 && (
            <ChartCard title="Rejection Reasons" icon={<XCircle size={14} />}>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={rejectionData} layout="vertical" barSize={14}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2e3150" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 10, fill: '#6c7193' }} />
                    <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 10, fill: '#6c7193' }} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Bar dataKey="count" fill="#ef4444" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          )}

          {/* Error categories */}
          {errorCatData.length > 0 && (
            <ChartCard title="Error Categories" icon={<BarChart2 size={14} />}>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={errorCatData} layout="vertical" barSize={14}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2e3150" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 10, fill: '#6c7193' }} />
                    <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 10, fill: '#6c7193' }} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Bar dataKey="count" fill="#f59e0b" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          )}
        </div>

        {/* Channel distribution (full width) */}
        <ChartCard title="Channel Distribution" icon={<User size={14} />}>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={channelData} barSize={32}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2e3150" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#6c7193' }} />
                <YAxis tick={{ fontSize: 10, fill: '#6c7193' }} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {channelData.map((_, i) => (
                    <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        {/* Daily progress */}
        {a.dailyProgress.length > 0 && (
          <ChartCard title="Review Progress Over Time" icon={<TrendingUp size={14} />}>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={a.dailyProgress}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2e3150" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6c7193' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#6c7193' }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Line type="monotone" dataKey="reviewed" stroke="#6366f1" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="approved" stroke="#22c55e" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        )}

        {/* ASR error table */}
        {a.asrErrors.length > 0 && (
          <div className="bg-surface-800/40 border border-surface-700/30 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-surface-700/30 flex items-center gap-2">
              <span className="text-accent-400"><BarChart2 size={14} /></span>
              <h2 className="text-sm font-semibold text-surface-100">Most Common ASR Errors</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-surface-700/30">
                    <th className="text-left px-4 py-2 text-surface-400 font-medium">ASR Output</th>
                    <th className="text-left px-4 py-2 text-surface-400 font-medium">Correct</th>
                    <th className="text-right px-4 py-2 text-surface-400 font-medium">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {a.asrErrors.slice(0, 20).map((err, i) => (
                    <tr
                      key={i}
                      className="border-b border-surface-700/20 hover:bg-surface-700/20 transition-colors"
                    >
                      <td className="px-4 py-2 text-danger-300 font-mono" dir="auto">{err.asr}</td>
                      <td className="px-4 py-2 text-success-300 font-mono" dir="auto">{err.correct}</td>
                      <td className="px-4 py-2 text-surface-300 text-right font-medium">{err.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
