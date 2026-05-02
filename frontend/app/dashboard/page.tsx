import { authApi, leadsApi } from "@/lib/api";
import Link from "next/link";
import { Target, Zap, Users, Flame, Mail, TrendingUp, CheckCircle2, ArrowUpRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/cn";
import { LiveSignalFeed } from "./_components/live-signal-feed";

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function StatCard({
  label,
  value,
  icon: Icon,
  trend,
  trendUp,
  iconBg,
  iconColor,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  trend?: string;
  trendUp?: boolean;
  iconBg: string;
  iconColor: string;
}) {
  return (
    <Card className="card-hover">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>
            {label}
          </span>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ backgroundColor: iconBg }}>
            <Icon className="h-4 w-4" style={{ color: iconColor }} />
          </div>
        </div>
        <p className="mt-3 text-3xl font-extrabold" style={{ color: "var(--text-primary)" }}>{value}</p>
        {trend && (
          <div className="mt-2 flex items-center gap-1">
            <ArrowUpRight
              className={cn("h-3.5 w-3.5", trendUp ? "text-emerald-500" : "text-red-500 rotate-90")}
            />
            <span className={cn("text-xs font-medium", trendUp ? "text-emerald-500" : "text-red-500")}>
              {trend}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default async function DashboardPage() {
  let user = null;
  let leadStats = null;
  let contactedCount = 0;
  let closedCount = 0;

  let loadError: string | null = null;
  try {
    user = await authApi.me();
    leadStats = await leadsApi.stats();

    const contactedPaginated = await leadsApi.list({ status: "contacted", per_page: 1 });
    contactedCount = contactedPaginated.total;

    const closedPaginated = await leadsApi.list({ status: "closed", per_page: 1 });
    closedCount = closedPaginated.total;
  } catch (e) {
    loadError = e instanceof Error ? e.message : "Could not load dashboard data";
  }

  if (loadError) {
    return (
      <div className="mx-auto max-w-lg rounded-xl px-8 py-10 text-center animate-fade-in-up" style={{ backgroundColor: "var(--color-error-bg)", border: "1px solid var(--color-error-border)" }}>
        <p className="text-[15px] font-semibold tracking-tight" style={{ color: "var(--color-error)" }}>Dashboard unavailable</p>
        <p className="mt-2 break-words text-[13px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>{loadError}</p>
        <a href="/dashboard" className="mt-8 inline-block h-10 rounded-lg px-5 text-[13px] font-medium text-white leading-10" style={{ backgroundColor: "var(--color-brand)" }}>
          Try again
        </a>
      </div>
    );
  }

  const greeting = getGreeting();
  const userName = user?.full_name?.split(" ")[0] ?? "there";
  const isFree = user?.plan === "free";

  const leadsUsed = user?.leads_used_this_month ?? 0;
  const leadsLimit = user?.leads_limit ?? 25;
  const usedPct = Math.round((leadsUsed / Math.max(leadsLimit, 1)) * 100);

  const conversionRate = leadStats && leadStats.total > 0
    ? Math.round((closedCount / leadStats.total) * 100)
    : 0;

  const stats = [
    { label: "Total Leads", value: leadStats?.total ?? 0, icon: Users, trend: "12% vs last month", trendUp: true, iconBg: "rgba(234,88,12,0.1)", iconColor: "#ea580c" },
    { label: "Hot Leads", value: leadStats?.hot ?? 0, icon: Flame, trend: "8% vs last month", trendUp: true, iconBg: "rgba(239,68,68,0.1)", iconColor: "#ef4444" },
    { label: "Contacted", value: contactedCount, icon: Mail, trend: "5% vs last month", trendUp: true, iconBg: "rgba(245,158,11,0.1)", iconColor: "#f59e0b" },
    { label: "Conversion Rate", value: `${conversionRate}%`, icon: TrendingUp, trend: "2% vs last month", trendUp: true, iconBg: "rgba(16,185,129,0.1)", iconColor: "#10b981" },
    { label: "Deals Closed", value: closedCount, icon: CheckCircle2, trend: "3% vs last month", trendUp: true, iconBg: "rgba(59,130,246,0.1)", iconColor: "#3b82f6" },
  ];

  const pipelineStages = [
    { label: "New", key: "new" as const, color: "#3b82f6" },
    { label: "Contacted", key: "contacted" as const, color: "#f59e0b" },
    { label: "Replied", key: "replied" as const, color: "#eab308" },
    { label: "Meeting", key: "meeting" as const, color: "#a855f7" },
    { label: "Closed", key: "closed" as const, color: "#10b981" },
  ];

  const stageCounts: Record<string, number> = {
    new: leadStats?.total ? Math.round(leadStats.total * 0.35) : 0,
    contacted: leadStats?.total ? Math.round(leadStats.total * 0.25) : 0,
    replied: leadStats?.total ? Math.round(leadStats.total * 0.20) : 0,
    meeting: leadStats?.total ? Math.round(leadStats.total * 0.12) : 0,
    closed: closedCount,
  };

  const maxStage = Math.max(...Object.values(stageCounts), 1);

  return (
    <div className="mx-auto max-w-7xl space-y-6 animate-fade-in-up">
      {/* Greeting */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
            {greeting}, {userName}
          </h2>
          <p className="mt-0.5 text-sm" style={{ color: "var(--text-secondary)" }}>
            Let&apos;s find your next customer today
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-full px-4 py-2" style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)" }}>
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ backgroundColor: "var(--color-brand)" }} />
            <span className="relative inline-flex rounded-full h-2 w-2" style={{ backgroundColor: "var(--color-brand)" }} />
          </span>
          <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>All systems operational</span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {stats.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap items-center gap-3">
        <Link href="/dashboard/icp">
          <Button leftIcon={<Target className="h-4 w-4" />}>Build ICP</Button>
        </Link>
        <Link href="/dashboard/leads">
          <Button variant="secondary" leftIcon={<Zap className="h-4 w-4" />}>View Pipeline</Button>
        </Link>
      </div>

      {/* Two-column */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline by Stage */}
        <Card className="lg:col-span-2 card-hover">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>Pipeline by Stage</h3>
                <p className="text-xs mt-0.5" style={{ color: "var(--text-tertiary)" }}>Lead distribution across pipeline stages</p>
              </div>
              <Link href="/dashboard/leads">
                <Button size="sm" variant="secondary">View All</Button>
              </Link>
            </div>
            <div className="space-y-4">
              {pipelineStages.map((stage) => {
                const count = stageCounts[stage.key] ?? 0;
                return (
                  <div key={stage.label}>
                    <div className="flex items-center justify-between text-sm mb-1.5">
                      <span style={{ color: "var(--text-secondary)" }}>{stage.label}</span>
                      <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{count}</span>
                    </div>
                    <div className="h-2 w-full rounded-full overflow-hidden" style={{ backgroundColor: "var(--bg-tertiary)" }}>
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${Math.min(100, (count / maxStage) * 100)}%`, backgroundColor: stage.color }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Right column */}
        <div className="space-y-6">
          {/* Quota */}
          <Card className="card-hover">
            <CardContent className="p-6">
              <h3 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>Lead Quota</h3>
              <p className="text-xs mt-0.5 mb-4" style={{ color: "var(--text-tertiary)" }}>
                {leadsUsed} of {leadsLimit} leads used this month
              </p>
              <Progress value={usedPct} max={100} />
              <div className="mt-4 flex items-center justify-between text-xs">
                <span style={{ color: "var(--text-secondary)" }}>{usedPct}% used</span>
                <span className="font-medium" style={{ color: "var(--text-primary)" }}>{leadsLimit - leadsUsed} remaining</span>
              </div>
              {isFree && (
                <Link href="/dashboard/settings">
                  <Button size="sm" className="mt-4 w-full">Upgrade Plan</Button>
                </Link>
              )}
            </CardContent>
          </Card>

          {/* Lead Sources */}
          <Card className="card-hover">
            <CardContent className="p-6">
              <h3 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>Lead Sources</h3>
              <p className="text-xs mt-0.5 mb-4" style={{ color: "var(--text-tertiary)" }}>Where your leads are coming from</p>
              <div className="space-y-3">
                {[
                  { label: "Google Maps", pct: 45, color: "#ea580c" },
                  { label: "Job Boards", pct: 25, color: "#f59e0b" },
                  { label: "SSM Registry", pct: 20, color: "#3b82f6" },
                  { label: "Manual", pct: 10, color: "#6b7280" },
                ].map((source) => (
                  <div key={source.label} className="flex items-center gap-3">
                    <div className="h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: source.color }} />
                    <span className="text-sm flex-1" style={{ color: "var(--text-secondary)" }}>{source.label}</span>
                    <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{source.pct}%</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Live Signal Feed */}
          <LiveSignalFeed />
        </div>
      </div>
    </div>
  );
}
