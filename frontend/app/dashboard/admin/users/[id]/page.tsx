import { adminApi, type AgencyDetail } from "@/lib/api";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Shield, CheckCircle2, XCircle } from "lucide-react";

export const dynamic = "force-dynamic";

const PLAN_COLORS: Record<string, string> = {
  free:    "bg-gray-800 text-gray-400",
  starter: "bg-blue-900/60 text-blue-300",
  growth:  "bg-indigo-900/60 text-indigo-300",
  pro:     "bg-purple-900/60 text-purple-300",
  agency:  "bg-orange-900/60 text-orange-300",
};

const TIER_COLORS: Record<string, string> = {
  hot:       "text-red-400",
  warm:      "text-orange-400",
  potential: "text-yellow-400",
  cold:      "text-blue-400",
};

export default async function AdminUserDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const detail: AgencyDetail | null = await adminApi.getUser(id).catch(() => null);

  if (!detail) notFound();

  const { user, leads, icps, pipeline_summary, recent_activity } = detail;

  const scoreDistribution = {
    hot:       leads.filter((l) => l.lead_score >= 85).length,
    warm:      leads.filter((l) => l.lead_score >= 60 && l.lead_score < 85).length,
    potential: leads.filter((l) => l.lead_score >= 40 && l.lead_score < 60).length,
    cold:      leads.filter((l) => l.lead_score < 40).length,
  };

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Back */}
      <Link
        href="/dashboard/admin/users"
        className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-white transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> Back to Users
      </Link>

      {/* Agency profile card */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-6">
        <div className="flex items-start gap-6 flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-xl font-black text-white">
                {user.company_name || user.full_name}
              </h1>
              {user.role === "admin" && (
                <span className="flex items-center gap-1 rounded-full bg-red-900/60 px-2 py-0.5 text-xs font-semibold text-red-300">
                  <Shield className="h-3 w-3" /> Admin
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500">{user.email}</p>
          </div>

          <div className="flex flex-wrap gap-3">
            <div className="rounded-lg bg-gray-800 px-4 py-3 text-center min-w-[90px]">
              <p className="text-[10px] uppercase tracking-wider text-gray-600 mb-1">Plan</p>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${PLAN_COLORS[user.plan] ?? "bg-gray-800 text-gray-400"}`}>
                {user.plan}
              </span>
            </div>
            <div className="rounded-lg bg-gray-800 px-4 py-3 text-center min-w-[90px]">
              <p className="text-[10px] uppercase tracking-wider text-gray-600 mb-1">Leads</p>
              <p className="text-xl font-black text-white">{user.lead_count.toLocaleString()}</p>
            </div>
            <div className="rounded-lg bg-gray-800 px-4 py-3 text-center min-w-[90px]">
              <p className="text-[10px] uppercase tracking-wider text-gray-600 mb-1">ICPs</p>
              <p className="text-xl font-black text-white">{user.icp_count}</p>
            </div>
            <div className="rounded-lg bg-gray-800 px-4 py-3 text-center min-w-[90px]">
              <p className="text-[10px] uppercase tracking-wider text-gray-600 mb-1">Status</p>
              {user.is_active ? (
                <span className="flex items-center gap-1 text-emerald-400 text-xs font-semibold justify-center">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Active
                </span>
              ) : (
                <span className="flex items-center gap-1 text-red-400 text-xs font-semibold justify-center">
                  <XCircle className="h-3.5 w-3.5" /> Inactive
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 border-t border-gray-800 pt-4">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-gray-600">Joined</p>
            <p className="text-sm text-gray-300 mt-0.5">
              {new Date(user.created_at).toLocaleDateString("en-MY", { day: "numeric", month: "long", year: "numeric" })}
            </p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-gray-600">Last Login</p>
            <p className="text-sm text-gray-300 mt-0.5">
              {user.last_login
                ? new Date(user.last_login).toLocaleDateString("en-MY", { day: "numeric", month: "long", year: "numeric" })
                : "Never"}
            </p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-gray-600">Role</p>
            <p className="text-sm text-gray-300 mt-0.5 capitalize">{user.role}</p>
          </div>
        </div>
      </div>

      {/* Middle row: ICPs | Pipeline | Score Distribution */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* ICPs */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
          <h2 className="text-sm font-bold text-white mb-4">ICPs ({icps.length})</h2>
          {icps.length === 0 ? (
            <p className="text-sm text-gray-600">No ICPs created</p>
          ) : (
            <div className="space-y-3">
              {icps.map((icp) => (
                <div key={icp.id} className="rounded-lg bg-gray-800 p-3">
                  <p className="text-sm font-semibold text-white">{icp.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5 truncate">
                    {icp.industries?.slice(0, 2).join(", ") || "—"}
                  </p>
                  <p className="text-xs text-gray-600 mt-0.5 truncate">
                    {icp.locations?.slice(0, 2).join(", ") || "—"}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pipeline summary */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
          <h2 className="text-sm font-bold text-white mb-4">Pipeline</h2>
          {Object.keys(pipeline_summary).length === 0 ? (
            <p className="text-sm text-gray-600">No pipeline entries</p>
          ) : (
            <div className="space-y-2">
              {Object.entries(pipeline_summary).map(([stage, count]) => (
                <div key={stage} className="flex items-center justify-between">
                  <span className="text-sm text-gray-400 capitalize">{stage.replace("_", " ")}</span>
                  <span className="text-sm font-bold text-white tabular-nums">{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Score distribution */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
          <h2 className="text-sm font-bold text-white mb-4">Lead Score Distribution</h2>
          <div className="space-y-3">
            {(["hot", "warm", "potential", "cold"] as const).map((tier) => (
              <div key={tier} className="flex items-center justify-between">
                <span className={`text-sm font-semibold capitalize ${TIER_COLORS[tier]}`}>{tier}</span>
                <span className="text-sm font-bold text-white tabular-nums">
                  {scoreDistribution[tier]}
                </span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-gray-600">Based on last 10 leads shown below</p>
        </div>
      </div>

      {/* Recent leads table */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm font-bold text-white">Recent Leads (last 10)</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                {["Company", "Contact", "Score", "Type", "Status", "Date"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-600">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {leads.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-600">No leads yet</td>
                </tr>
              )}
              {leads.map((lead) => (
                <tr key={lead.id} className="border-b border-gray-800/50 hover:bg-gray-800/20">
                  <td className="px-4 py-3 text-gray-200 font-medium">{lead.company_name || "—"}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{lead.person_name || "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`font-bold tabular-nums ${TIER_COLORS[lead.lead_tier] ?? "text-gray-400"}`}>
                      {lead.lead_score}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs rounded-full bg-gray-800 px-2 py-0.5 text-gray-400 uppercase">
                      {lead.lead_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 capitalize text-xs">{lead.status}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs whitespace-nowrap">
                    {lead.created_at
                      ? new Date(lead.created_at).toLocaleDateString("en-MY", { day: "numeric", month: "short" })
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent activity */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
        <h2 className="text-sm font-bold text-white mb-4">Recent Activity (last 20)</h2>
        {recent_activity.length === 0 ? (
          <p className="text-sm text-gray-600">No activity recorded</p>
        ) : (
          <div className="space-y-2">
            {recent_activity.map((ev, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                <span className="mt-0.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-orange-500" />
                <div className="flex-1 min-w-0">
                  <span className="text-gray-300">{ev.event_type}</span>
                  {ev.new_value && (
                    <span className="text-gray-500 ml-2">→ {ev.new_value}</span>
                  )}
                  {ev.note && (
                    <span className="text-gray-600 ml-2 text-xs">{ev.note}</span>
                  )}
                </div>
                <span className="text-xs text-gray-700 whitespace-nowrap">
                  {ev.created_at
                    ? new Date(ev.created_at).toLocaleDateString("en-MY", { day: "numeric", month: "short" })
                    : "—"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
