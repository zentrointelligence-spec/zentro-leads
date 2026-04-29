import { authApi, leadsApi } from "@/lib/api";
import Link from "next/link";
import { Users, Flame, TrendingUp, Zap, ArrowRight, Target } from "lucide-react";

export default async function DashboardPage() {
  let user = null;
  let leadStats = null;

  try {
    user = await authApi.me();
    leadStats = await leadsApi.stats();
  } catch {
    // Not authenticated — layout redirects to login
  }

  const leadsUsed = user?.leads_used_this_month ?? 0;
  const leadsLimit = user?.leads_limit ?? 25;
  const usedPct = Math.round((leadsUsed / Math.max(leadsLimit, 1)) * 100);

  const stats = [
    {
      label: "Leads This Month",
      value: leadsUsed,
      sub: `of ${leadsLimit} limit`,
      icon: Users,
      tone: "from-indigo-400/90 to-violet-500/90",
    },
    {
      label: "Hot Leads",
      value: leadStats?.hot ?? "—",
      sub: "score ≥ 85",
      icon: Flame,
      tone: "from-orange-400/90 to-rose-500/90",
    },
    {
      label: "Warm Leads",
      value: leadStats?.warm ?? "—",
      sub: "score 60–84",
      icon: TrendingUp,
      tone: "from-amber-300/90 to-yellow-500/90",
    },
  ];

  return (
    <div className="space-y-8 animate-fade-up">
      <div className="relative overflow-hidden rounded-2xl border border-[color:var(--border-color)] bg-[color:var(--card-bg)] p-6 shadow-[var(--shadow-md)] backdrop-blur-xl md:p-8">
        <div
          className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full blur-3xl"
          style={{
            background: "radial-gradient(circle, rgba(99,102,241,0.2) 0%, transparent 70%)",
          }}
        />
        <h2 className="text-2xl font-bold tracking-tight text-[color:var(--text-primary)]">
          Welcome back{user ? `, ${user.full_name.split(" ")[0]}` : ""}
        </h2>
        <p className="mt-2 text-sm text-[color:var(--text-secondary)]">
          Here&apos;s what&apos;s happening with your leads today.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {stats.map(({ label, value, sub, icon: Icon, tone }, i) => (
          <div
            key={label}
            className="gradient-border-wrap glow-hover animate-fade-up"
            style={{ animationDelay: `${i * 70}ms` }}
          >
            <div className="gradient-border-inner glass-panel rounded-2xl p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-[color:var(--text-muted)] mb-2">
                    {label}
                  </p>
                  <p className="text-3xl font-bold text-[color:var(--text-primary)]">{value}</p>
                  <p className="text-xs mt-1 text-[color:var(--text-muted)]">{sub}</p>
                </div>
                <div
                  className={`rounded-xl bg-gradient-to-br p-2.5 ring-1 ring-[color:var(--border-color)] ${tone}`}
                >
                  <Icon className="h-5 w-5 text-white drop-shadow-sm" />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="gradient-border-wrap glow-hover">
        <div className="gradient-border-inner glass-panel rounded-2xl p-5">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold text-[color:var(--text-primary)]">Lead quota</p>
            <span className="text-xs tabular-nums text-[color:var(--text-secondary)]">
              {leadsUsed} / {leadsLimit} used
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-[color:var(--border-color)]/70">
            <div
              className="h-full origin-left rounded-full bg-[image:var(--accent-gradient)] transition-transform duration-700 ease-out"
              style={{ transform: `scaleX(${usedPct / 100})` }}
            />
          </div>
          <p className="mt-2 text-xs text-[color:var(--text-muted)]">
            {user?.plan === "free"
              ? "Upgrade to get more leads per month"
              : `${user?.plan} plan`}
          </p>
        </div>
      </div>

      <div>
        <h3 className="mb-3 text-lg font-semibold text-[color:var(--text-primary)]">Quick actions</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Link
            href="/dashboard/leads"
            className="group flex items-center gap-3 rounded-2xl border border-[color:var(--border-color)] bg-[color:var(--card-bg)] p-4 backdrop-blur-xl transition-all hover:border-[color:var(--accent)]/40 hover:shadow-[var(--shadow-glow)]"
          >
            <div className="rounded-xl bg-[color:var(--accent-soft)] p-2">
              <Zap className="h-4 w-4 text-[color:var(--accent)]" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-[color:var(--text-primary)]">Generate Leads</p>
              <p className="text-xs text-[color:var(--text-muted)]">AI-powered search</p>
            </div>
            <ArrowRight className="h-4 w-4 text-[color:var(--text-muted)] transition group-hover:text-[color:var(--accent)]" />
          </Link>

          <Link
            href="/dashboard/icp"
            className="group flex items-center gap-3 rounded-2xl border border-[color:var(--border-color)] bg-[color:var(--card-bg)] p-4 backdrop-blur-xl transition-all hover:border-[color:var(--accent)]/40 hover:shadow-[var(--shadow-glow)]"
          >
            <div className="rounded-xl bg-purple-500/10 p-2">
              <Target className="h-4 w-4 text-purple-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-[color:var(--text-primary)]">Create ICP</p>
              <p className="text-xs text-[color:var(--text-muted)]">Define your target</p>
            </div>
            <ArrowRight className="h-4 w-4 text-[color:var(--text-muted)] transition group-hover:text-[color:var(--accent)]" />
          </Link>

          <Link
            href="/dashboard/leads"
            className="group flex items-center gap-3 rounded-2xl border border-[color:var(--border-color)] bg-[color:var(--card-bg)] p-4 backdrop-blur-xl transition-all hover:border-[color:var(--accent)]/40 hover:shadow-[var(--shadow-glow)]"
          >
            <div className="rounded-xl bg-emerald-500/10 p-2">
              <Users className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-[color:var(--text-primary)]">View All Leads</p>
              <p className="text-xs text-[color:var(--text-muted)]">Manage pipeline</p>
            </div>
            <ArrowRight className="h-4 w-4 text-[color:var(--text-muted)] transition group-hover:text-[color:var(--accent)]" />
          </Link>
        </div>
      </div>
    </div>
  );
}
