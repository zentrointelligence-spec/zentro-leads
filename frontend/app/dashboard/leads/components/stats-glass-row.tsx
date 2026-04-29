"use client";

import { Flame, TrendingUp, Users } from "lucide-react";

import type { LeadStats } from "@/lib/api";
import { cn } from "@/lib/cn";

interface Props {
  stats: LeadStats;
  leadsUsed: number;
  leadsLimit: number;
}

/**
 * Glass stat cards with gradient border wrap, hover glow, animated quota bar.
 */
export function StatsGlassRow({ stats, leadsUsed, leadsLimit }: Props) {
  const usedPct = Math.min(100, Math.round((leadsUsed / Math.max(leadsLimit, 1)) * 100));

  const cards = [
    {
      label: "Hot pipeline",
      value: stats.hot,
      sub: "Score ≥ 85",
      icon: Flame,
      barPct: Math.min(100, stats.total ? (stats.hot / stats.total) * 100 : 0),
      tone: "from-orange-400/90 to-rose-500/90",
    },
    {
      label: "Warm opportunities",
      value: stats.warm,
      sub: "Score 60–84",
      icon: TrendingUp,
      barPct: Math.min(100, stats.total ? (stats.warm / stats.total) * 100 : 0),
      tone: "from-amber-300/90 to-yellow-500/90",
    },
    {
      label: "Total in CRM",
      value: stats.total,
      sub: "All tiers",
      icon: Users,
      barPct: 100,
      tone: "from-indigo-400/90 to-violet-500/90",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {cards.map(({ label, value, sub, icon: Icon, barPct, tone }, i) => (
          <div
            key={label}
            className="gradient-border-wrap glow-hover animate-fade-up"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className="gradient-border-inner glass-panel rounded-2xl p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-[color:var(--text-muted)] mb-2">
                    {label}
                  </p>
                  <p className="text-3xl font-bold tabular-nums text-[color:var(--text-primary)]">
                    {value}
                  </p>
                  <p className="text-xs mt-1 text-[color:var(--text-secondary)]">{sub}</p>
                </div>
                <div
                  className={cn(
                    "rounded-xl p-2.5 bg-gradient-to-br shadow-inner",
                    "ring-1 ring-[color:var(--border-color)]",
                    tone
                  )}
                >
                  <Icon className="h-5 w-5 text-white drop-shadow-sm" />
                </div>
              </div>
              <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-[color:var(--border-color)]/60">
                <div
                  className={cn("h-full origin-left rounded-full bg-gradient-to-r animate-bar", tone)}
                  style={{ transform: `scaleX(${barPct / 100})` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="gradient-border-wrap glow-hover animate-fade-up">
        <div className="gradient-border-inner glass-panel rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold text-[color:var(--text-primary)]">Monthly quota</p>
            <span className="text-xs tabular-nums text-[color:var(--text-secondary)]">
              {leadsUsed} / {leadsLimit} used
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-[color:var(--border-color)]/70">
            <div
              className="h-full origin-left rounded-full bg-[image:var(--accent-gradient)] animate-bar shadow-[0_0_12px_var(--accent-glow)]"
              style={{ transform: `scaleX(${usedPct / 100})` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
