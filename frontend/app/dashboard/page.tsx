import { authApi, leadsApi } from "@/lib/api";
import Link from "next/link";
import { Users, Flame, TrendingUp, Zap, ArrowRight, Target } from "lucide-react";

export default async function DashboardPage() {
  let user = null;
  let leads = null;

  try {
    user = await authApi.me();
    leads = await leadsApi.list({ per_page: 1 });
  } catch {
    // Not authenticated — middleware will redirect
  }

  const leadsUsed = user?.leads_used_this_month ?? 0;
  const leadsLimit = user?.leads_limit ?? 25;
  const usedPct = Math.round((leadsUsed / leadsLimit) * 100);

  const stats = [
    {
      label: "Leads This Month",
      value: leadsUsed,
      sub: `of ${leadsLimit} limit`,
      icon: Users,
      color: "text-[#3B6FFF]",
      bg: "bg-[#3B6FFF]/10",
    },
    {
      label: "Hot Leads",
      value: "—",
      sub: "score ≥ 85",
      icon: Flame,
      color: "text-orange-400",
      bg: "bg-orange-400/10",
    },
    {
      label: "Warm Leads",
      value: "—",
      sub: "score 60–84",
      icon: TrendingUp,
      color: "text-yellow-400",
      bg: "bg-yellow-400/10",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div>
        <h2 className="text-white text-xl font-semibold">
          Welcome back{user ? `, ${user.full_name.split(" ")[0]}` : ""}!
        </h2>
        <p className="text-slate-400 text-sm mt-1">
          Here&apos;s what&apos;s happening with your leads today.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {stats.map(({ label, value, sub, icon: Icon, color, bg }) => (
          <div
            key={label}
            className="bg-[#0F1B2D] border border-white/8 rounded-xl p-5"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-slate-400 text-xs font-medium uppercase tracking-wide mb-2">
                  {label}
                </p>
                <p className="text-white text-3xl font-bold">{value}</p>
                <p className="text-slate-500 text-xs mt-1">{sub}</p>
              </div>
              <div className={`${bg} p-2.5 rounded-lg`}>
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Usage bar */}
      <div className="bg-[#0F1B2D] border border-white/8 rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <p className="text-white text-sm font-medium">Lead Quota</p>
          <span className="text-slate-400 text-xs">
            {leadsUsed} / {leadsLimit} used
          </span>
        </div>
        <div className="h-2 bg-white/8 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#3B6FFF] rounded-full transition-all"
            style={{ width: `${usedPct}%` }}
          />
        </div>
        <p className="text-slate-500 text-xs mt-2">
          {user?.plan === "free"
            ? "Upgrade to get more leads per month"
            : `${user?.plan} plan`}
        </p>
      </div>

      {/* Quick actions */}
      <div>
        <h3 className="text-white text-sm font-semibold mb-3">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Link
            href="/dashboard/leads"
            className="flex items-center gap-3 p-4 bg-[#0F1B2D] border border-white/8 rounded-xl hover:border-[#3B6FFF]/40 hover:bg-[#3B6FFF]/5 transition-all group"
          >
            <div className="bg-[#3B6FFF]/10 p-2 rounded-lg">
              <Zap className="w-4 h-4 text-[#3B6FFF]" />
            </div>
            <div className="flex-1">
              <p className="text-white text-sm font-medium">Generate Leads</p>
              <p className="text-slate-500 text-xs">AI-powered search</p>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-[#3B6FFF] transition-colors" />
          </Link>

          <Link
            href="/dashboard/icp"
            className="flex items-center gap-3 p-4 bg-[#0F1B2D] border border-white/8 rounded-xl hover:border-[#3B6FFF]/40 hover:bg-[#3B6FFF]/5 transition-all group"
          >
            <div className="bg-purple-500/10 p-2 rounded-lg">
              <Target className="w-4 h-4 text-purple-400" />
            </div>
            <div className="flex-1">
              <p className="text-white text-sm font-medium">Create ICP</p>
              <p className="text-slate-500 text-xs">Define your target</p>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-[#3B6FFF] transition-colors" />
          </Link>

          <Link
            href="/dashboard/leads"
            className="flex items-center gap-3 p-4 bg-[#0F1B2D] border border-white/8 rounded-xl hover:border-[#3B6FFF]/40 hover:bg-[#3B6FFF]/5 transition-all group"
          >
            <div className="bg-green-500/10 p-2 rounded-lg">
              <Users className="w-4 h-4 text-green-400" />
            </div>
            <div className="flex-1">
              <p className="text-white text-sm font-medium">View All Leads</p>
              <p className="text-slate-500 text-xs">Manage pipeline</p>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-[#3B6FFF] transition-colors" />
          </Link>
        </div>
      </div>
    </div>
  );
}
