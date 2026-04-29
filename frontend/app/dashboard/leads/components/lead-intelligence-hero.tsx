"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";

import { AiPulseDot } from "@/app/dashboard/_components/ai-pulse-dot";
import { ThemeToggle } from "@/app/dashboard/_components/theme-toggle";
import { cn } from "@/lib/cn";

/**
 * Hero band for Lead Intelligence: title, CTA, theme toggle, AI pulse.
 */
export function LeadIntelligenceHero({ className }: { className?: string }) {
  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-2xl border border-[color:var(--border-color)]",
        "bg-[color:var(--card-bg)] backdrop-blur-xl shadow-[var(--shadow-md)]",
        className
      )}
    >
      <div
        className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full blur-3xl"
        style={{
          background:
            "radial-gradient(circle at center, rgba(99,102,241,0.35) 0%, transparent 70%)",
        }}
      />
      <div
        className="pointer-events-none absolute -bottom-20 -left-16 h-56 w-56 rounded-full blur-3xl"
        style={{
          background:
            "radial-gradient(circle at center, rgba(56,189,248,0.22) 0%, transparent 70%)",
        }}
      />
      <div className="relative flex flex-col gap-6 p-6 md:flex-row md:items-center md:justify-between md:p-8">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold tracking-tight text-[color:var(--text-primary)]">
              Lead Intelligence
            </h2>
            <AiPulseDot />
          </div>
          <p className="text-sm text-[color:var(--text-secondary)] max-w-xl">
            AI-powered insights to close faster
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/dashboard/icp"
            className={cn(
              "inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold text-white",
              "bg-[image:var(--accent-gradient)] shadow-lg",
              "hover:shadow-[0_0_32px_rgba(99,102,241,0.45)] hover:scale-[1.02] transition-all duration-300",
              "btn-ripple"
            )}
          >
            <Sparkles className="h-4 w-4" />
            Generate Leads
          </Link>
          <ThemeToggle />
        </div>
      </div>
    </section>
  );
}
