import { adminApi, type QualityReport } from "@/lib/api";
import { AlertCircle, AlertTriangle } from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

export const dynamic = "force-dynamic";

function ProgressBar({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  const pct = Math.min(100, Math.max(0, Math.round(value)));
  const color = warn
    ? "bg-red-500"
    : pct >= 80
    ? "bg-emerald-500"
    : pct >= 60
    ? "bg-yellow-500"
    : "bg-red-500";

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm text-gray-300">{label}</span>
        <span className={`text-sm font-bold tabular-nums ${warn ? "text-red-400" : "text-white"}`}>
          {pct}%
        </span>
      </div>
      <div className="h-2.5 rounded-full bg-gray-800 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}

const PIE_COLORS = { hot: "#ef4444", warm: "#f97316", qualified: "#eab308", cold: "#3b82f6" };

export default async function AdminLeadsPage() {
  const report: QualityReport | null = await adminApi.getLeadQuality().catch(() => null);

  if (!report) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Failed to load quality report. Check backend connectivity.</p>
      </div>
    );
  }

  const pieData = [
    { name: "HOT",       value: report.score_distribution.hot,       color: PIE_COLORS.hot },
    { name: "WARM",      value: report.score_distribution.warm,       color: PIE_COLORS.warm },
    { name: "QUALIFIED", value: report.score_distribution.qualified,  color: PIE_COLORS.qualified },
    { name: "COLD",      value: report.score_distribution.cold,       color: PIE_COLORS.cold },
  ].filter((d) => d.value > 0);

  const sourceBarData = Object.entries(report.avg_score_by_source).map(([source, score]) => ({
    name:  source.replace(/_/g, " "),
    score: Math.round(score),
  }));

  const alerts: Array<{ level: "red" | "yellow"; message: string }> = [];

  if (report.email_verified_pct < 70)
    alerts.push({ level: "red", message: "Email verification rate below 70% — check SMTP verifier" });
  if (report.duplicate_rate > 5)
    alerts.push({ level: "red", message: `Duplicate rate ${report.duplicate_rate.toFixed(1)}% — elevated, check dedup logic` });
  if (report.leads_without_contact > 100)
    alerts.push({ level: "yellow", message: `${report.leads_without_contact.toLocaleString()} leads have no contact info` });

  return (
    <div className="space-y-8 max-w-5xl">
      <div>
        <h1 className="text-2xl font-black text-white">Lead Quality Report</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          {report.total_leads.toLocaleString()} total leads across all agencies
        </p>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-3">
          {alerts.map((a, i) => (
            <div
              key={i}
              className={`flex items-start gap-3 rounded-xl px-4 py-3 border ${
                a.level === "red"
                  ? "bg-red-950/40 border-red-900 text-red-300"
                  : "bg-yellow-950/40 border-yellow-900 text-yellow-300"
              }`}
            >
              {a.level === "red" ? (
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
              )}
              <p className="text-sm">{a.message}</p>
            </div>
          ))}
        </div>
      )}

      {/* ROW 1 — Quality progress bars */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-6">
        <h2 className="text-sm font-bold text-white mb-5">Data Coverage</h2>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <ProgressBar label="Email Verified" value={report.email_verified_pct} />
          <ProgressBar label="Phone Present"  value={report.phone_present_pct} />
          <ProgressBar label="Duplicate Rate" value={report.duplicate_rate} warn />
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm text-gray-300">Leads Without Contact</span>
              <span className="text-sm font-bold text-white tabular-nums">
                {report.leads_without_contact.toLocaleString()}
              </span>
            </div>
            <div className="h-2.5 rounded-full bg-gray-800" />
          </div>
        </div>
      </div>

      {/* ROW 2 — Score distribution donut + source bar */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Donut */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-6">
          <h2 className="text-sm font-bold text-white mb-4">Score Distribution</h2>
          {pieData.length === 0 ? (
            <p className="text-sm text-gray-600 py-8 text-center">No leads yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={110}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
                  itemStyle={{ color: "#f9fafb" }}
                  formatter={(value, name) => [`${value ?? 0}`, String(name)]}
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  formatter={(value) => (
                    <span className="text-xs text-gray-400">{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Avg score by source */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-6">
          <h2 className="text-sm font-bold text-white mb-4">Avg Score by Source</h2>
          {sourceBarData.length === 0 ? (
            <p className="text-sm text-gray-600 py-8 text-center">No data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={sourceBarData} margin={{ bottom: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#9ca3af", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  angle={-30}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: "#6b7280", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
                  itemStyle={{ color: "#f97316" }}
                  formatter={(v) => [`${v ?? 0} / 100`, "Avg Score"]}
                />
                <Bar dataKey="score" fill="#f97316" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Raw numbers */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: "HOT",       value: report.score_distribution.hot,      color: "text-red-400" },
          { label: "WARM",      value: report.score_distribution.warm,     color: "text-orange-400" },
          { label: "QUALIFIED", value: report.score_distribution.qualified, color: "text-yellow-400" },
          { label: "COLD",      value: report.score_distribution.cold,     color: "text-blue-400" },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-xl bg-gray-900 border border-gray-800 p-4 text-center">
            <p className={`text-xs font-bold uppercase tracking-wider mb-1 ${color}`}>{label}</p>
            <p className="text-2xl font-black text-white tabular-nums">{value.toLocaleString()}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
