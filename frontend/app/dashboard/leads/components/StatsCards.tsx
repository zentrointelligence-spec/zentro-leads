"use client";

import { memo, useMemo } from "react";
import type { LeadStats } from "@/lib/api";
import { Flame, Percent, Snowflake, Target, TrendingUp, Users } from "lucide-react";

interface Props {
  stats: LeadStats;
}

const TOOLTIP =
  "Leads categorized based on AI scoring tiers (hot, warm, potential, cold) and your plan quota.";

function MiniBar({ ratio }: { ratio: number }) {
  const w = Math.min(100, Math.max(0, Math.round(ratio * 100)));
  return (
    <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
      <div
        className="h-full rounded-full bg-gradient-to-r from-brand-blue/80 to-blue-400/90 transition-[width] duration-500 ease-out"
        style={{ width: `${w}%` }}
      />
    </div>
  );
}

function TrendPlaceholder() {
  return (
    <span className="inline-flex items-center gap-0.5 text-[10px] font-medium tabular-nums text-zinc-600">
      <span className="text-emerald-500/80">↑</span>
      <span className="text-zinc-600">—</span>
    </span>
  );
}

/**
 * KPI strip — neutral surfaces, tooltips, mini trend placeholders, and share bars.
 */
export const StatsCards = memo(function StatsCards({ stats }: Props) {
  const cards = useMemo(() => {
    const totalSafe = Math.max(1, stats.total);
    return [
      {
        label: "Hot",
        value: stats.hot,
        sub: "Score ≥ 85",
        icon: Flame,
        accent: "bg-red-500",
        barRatio: stats.hot / totalSafe,
      },
      {
        label: "Warm",
        value: stats.warm,
        sub: "Score 60–84",
        icon: TrendingUp,
        accent: "bg-amber-400",
        barRatio: stats.warm / totalSafe,
      },
      {
        label: "Potential",
        value: stats.potential,
        sub: "Score 40–59",
        icon: Target,
        accent: "bg-blue-500",
        barRatio: stats.potential / totalSafe,
      },
      {
        label: "Cold",
        value: stats.cold,
        sub: "Lower tier in workspace",
        icon: Snowflake,
        accent: "bg-zinc-500",
        barRatio: stats.cold / totalSafe,
      },
      {
        label: "Total",
        value: stats.total,
        sub: "All leads",
        icon: Users,
        accent: "bg-blue-500",
        barRatio: (stats.hot + stats.warm + stats.potential) / totalSafe,
      },
      {
        label: "Quota",
        value: `${stats.limit_percentage.toFixed(0)}%`,
        sub: `${stats.used_this_month} / ${stats.limit} this month`,
        icon: Percent,
        accent: "bg-emerald-400",
        barRatio: stats.limit_percentage / 100,
      },
    ];
  }, [stats]);

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6 lg:gap-4">
      {cards.map((c) => (
        <div
          key={c.label}
          title={TOOLTIP}
          className="group relative cursor-default overflow-hidden rounded-lg border border-white/[0.06] bg-[#09090b]/70 px-4 py-4 shadow-sm shadow-black/20 transition-[border-color,background-color,box-shadow,transform] duration-200 ease-out hover:-translate-y-0.5 hover:border-white/[0.1] hover:bg-[#09090b]/90 hover:shadow-md sm:px-5 sm:py-5"
        >
          <div
            className={`absolute left-3 top-4 bottom-4 w-0.5 rounded-full ${c.accent} opacity-90`}
            aria-hidden
          />
          <div className="pl-4">
            <div className="flex items-start justify-between gap-2">
              <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
                {c.label}
              </p>
              <div className="flex flex-col items-end gap-1">
                <TrendPlaceholder />
                <c.icon className="h-3.5 w-3.5 shrink-0 text-zinc-600 transition-colors duration-200 group-hover:text-zinc-400" />
              </div>
            </div>
            <p className="mt-3 text-2xl font-semibold tabular-nums tracking-tight text-zinc-100">
              {c.value}
            </p>
            <p className="mt-1 text-[12px] leading-snug text-zinc-500">{c.sub}</p>
            <MiniBar ratio={Number.isFinite(c.barRatio) ? c.barRatio : 0} />
          </div>
        </div>
      ))}
    </div>
  );
});
