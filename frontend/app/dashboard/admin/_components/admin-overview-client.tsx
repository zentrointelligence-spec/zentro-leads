"use client";

import { useEffect, useState, useCallback } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import {
  Users,
  Flame,
  BarChart2,
  Activity,
  Target,
  Zap,
  Building2,
} from "lucide-react";
import type { PlatformStats, ActivityEvent } from "@/lib/api";
import { parseJsonResponse } from "@/lib/parse-json-client";
import { formatDistanceToNow } from "date-fns";

interface Props {
  initialStats:    PlatformStats | null;
  initialActivity: ActivityEvent[];
}

function StatCard({
  label,
  value,
  icon: Icon,
  color = "text-orange-400",
  sub,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color?: string;
  sub?: string;
}) {
  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          {label}
        </p>
        <Icon className={`h-4 w-4 ${color}`} />
      </div>
      <p className="text-3xl font-black text-white tabular-nums">
        {typeof value === "number" ? value.toLocaleString() : value}
      </p>
      {sub && <p className="mt-1 text-xs text-gray-500">{sub}</p>}
    </div>
  );
}

const EVENT_CONFIG: Record<string, { emoji: string; color: string }> = {
  user_registered: { emoji: "🟢", color: "text-emerald-400" },
  status_change:   { emoji: "📊", color: "text-blue-400" },
  zims_pushed:     { emoji: "🔗", color: "text-purple-400" },
  score_updated:   { emoji: "⚡", color: "text-yellow-400" },
};

function ActivityFeed({ events }: { events: ActivityEvent[] }) {
  return (
    <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
      {events.length === 0 && (
        <p className="text-sm text-gray-600 py-8 text-center">No recent activity</p>
      )}
      {events.map((ev, i) => {
        const cfg = EVENT_CONFIG[ev.event_type] ?? { emoji: "📌", color: "text-gray-400" };
        const ts = ev.timestamp
          ? formatDistanceToNow(new Date(ev.timestamp), { addSuffix: true })
          : "—";
        return (
          <div
            key={i}
            className="flex items-start gap-3 rounded-lg bg-gray-900 border border-gray-800 px-4 py-3"
          >
            <span className="text-base leading-none mt-0.5">{cfg.emoji}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-200 leading-snug">{ev.detail}</p>
              {ev.user_email && (
                <p className="text-xs text-gray-500 mt-0.5 truncate">{ev.user_email}</p>
              )}
            </div>
            <span className="text-xs text-gray-600 whitespace-nowrap ml-2">{ts}</span>
          </div>
        );
      })}
    </div>
  );
}

export function AdminOverviewClient({ initialStats, initialActivity }: Props) {
  const [stats, setStats]       = useState<PlatformStats | null>(initialStats);
  const [activity, setActivity] = useState<ActivityEvent[]>(initialActivity);
  const [loading, setLoading]   = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, actRes] = await Promise.all([
        fetch("/api/admin/stats"),
        fetch("/api/admin/activity"),
      ]);
      const s = await parseJsonResponse<PlatformStats | null>(statsRes, null);
      const a = await parseJsonResponse<ActivityEvent[]>(actRes, []);
      if (s && typeof s === "object" && "total_users" in s) setStats(s);
      setActivity(Array.isArray(a) ? a : []);
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-refresh activity every 60 seconds
  useEffect(() => {
    const id = setInterval(refresh, 60_000);
    return () => clearInterval(id);
  }, [refresh]);

  if (!stats) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        Failed to load platform stats. Check backend connectivity.
      </div>
    );
  }

  const industryData = (stats.top_industries ?? []).map((d) => ({
    name: d.industry.length > 16 ? d.industry.slice(0, 14) + "…" : d.industry,
    count: d.count,
  }));

  const locationData = (stats.top_locations ?? []).map((d) => ({
    name: d.city.length > 14 ? d.city.slice(0, 12) + "…" : d.city,
    count: d.count,
  }));

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Platform Overview</h1>
          <p className="text-sm text-gray-500 mt-0.5">Live metrics from all agencies</p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg bg-gray-800 border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 transition-colors disabled:opacity-50"
        >
          <Activity className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* ROW 1 — 6 stat cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
        <StatCard
          label="Total Users"
          value={stats.total_users}
          icon={Users}
          color="text-blue-400"
          sub={`${stats.active_users_today} active today`}
        />
        <StatCard
          label="Leads Today"
          value={stats.leads_generated_today}
          icon={Zap}
          color="text-yellow-400"
          sub={`${stats.leads_generated_this_week.toLocaleString()} this week`}
        />
        <StatCard
          label="HOT Leads"
          value={stats.hot_leads_total}
          icon={Flame}
          color="text-red-400"
          sub="Score ≥ 85"
        />
        <StatCard
          label="B2B Leads"
          value={stats.total_b2b_leads}
          icon={Building2}
          color="text-indigo-400"
        />
        <StatCard
          label="B2C Leads"
          value={stats.total_b2c_leads}
          icon={Target}
          color="text-pink-400"
        />
        <StatCard
          label="Avg Score"
          value={stats.average_lead_score.toFixed(1)}
          icon={BarChart2}
          color="text-emerald-400"
          sub={`${stats.total_leads_generated.toLocaleString()} total leads`}
        />
      </div>

      {/* ROW 2 — Charts */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {/* Top industries */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-6">
          <h2 className="text-sm font-bold text-white mb-4">Top Industries</h2>
          {industryData.length === 0 ? (
            <p className="text-sm text-gray-600 py-8 text-center">No data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={industryData} layout="vertical" margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
                <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={110}
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
                  labelStyle={{ color: "#f9fafb" }}
                  itemStyle={{ color: "#f97316" }}
                />
                <Bar dataKey="count" fill="#f97316" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top locations */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-6">
          <h2 className="text-sm font-bold text-white mb-4">Top Locations</h2>
          {locationData.length === 0 ? (
            <p className="text-sm text-gray-600 py-8 text-center">No data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={locationData} layout="vertical" margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
                <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={100}
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
                  labelStyle={{ color: "#f9fafb" }}
                  itemStyle={{ color: "#3b82f6" }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Extra stats row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Active This Week</p>
          <p className="text-2xl font-black text-white">{stats.active_users_this_week}</p>
        </div>
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Total ICPs</p>
          <p className="text-2xl font-black text-white">{stats.total_icps_created}</p>
        </div>
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">ZIMS Pushes</p>
          <p className="text-2xl font-black text-white">{stats.total_zims_pushes}</p>
        </div>
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Revenue (MTD)</p>
          <p className="text-2xl font-black text-white">
            {stats.revenue_this_month != null
              ? `$${stats.revenue_this_month.toLocaleString()}`
              : "—"}
          </p>
        </div>
      </div>

      {/* ROW 3 — Activity feed */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold text-white">Recent Activity</h2>
          <span className="text-xs text-gray-600">Auto-refreshes every 60s</span>
        </div>
        <ActivityFeed events={activity} />
      </div>
    </div>
  );
}
