"use client";

import { useEffect } from "react";
import { X } from "lucide-react";

import type { Lead } from "@/lib/api";
import {
  companyNameFromLead,
  explainLead,
  scoreBreakdownBars,
} from "@/lib/lead-view";
import { cn } from "@/lib/cn";

interface Props {
  lead: Lead | null;
  onClose: () => void;
}

function priorityFromTier(tier: string): string {
  switch (tier) {
    case "hot":
      return "Critical priority";
    case "warm":
      return "High priority";
    case "potential":
      return "Medium priority";
    default:
      return "Nurture";
  }
}

/**
 * Right-side AI intelligence panel for a single lead.
 */
export function LeadDrawer({ lead, onClose }: Props) {
  useEffect(() => {
    if (!lead) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lead, onClose]);

  if (!lead) return null;

  const company = companyNameFromLead(lead);
  const explain = explainLead(lead, lead.company);
  const bars = scoreBreakdownBars(lead);
  const outreach =
    lead.ai_whatsapp_msg ||
    lead.ai_email_body ||
    "No AI draft yet — generate outreach from the lead record once enrichment completes.";

  return (
    <>
      <button
        type="button"
        aria-label="Close panel"
        className="fixed inset-0 z-40 bg-[color:var(--text-primary)]/25 backdrop-blur-sm animate-fade-up"
        onClick={onClose}
      />
      <aside
        className={cn(
          "fixed inset-y-0 right-0 z-50 flex w-full max-w-full flex-col border-l shadow-2xl",
          "border-[color:var(--border-color)] bg-[color:var(--card-bg)] backdrop-blur-2xl",
          "animate-fade-up sm:max-w-lg"
        )}
      >
        <div className="flex items-center justify-between border-b border-[color:var(--border-color)] px-5 py-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-[color:var(--text-muted)]">
              AI lead brief
            </p>
            <h3 className="text-lg font-bold text-[color:var(--text-primary)]">{company}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-[color:var(--border-color)] p-2 text-[color:var(--text-secondary)] hover:bg-[color:var(--accent-soft)]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-6 space-y-6">
          {/* A. Summary */}
          <section className="rounded-2xl border border-[color:var(--border-color)] bg-[color:var(--accent-gradient-soft)] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm text-[color:var(--text-secondary)]">Lead score</p>
                <p className="text-3xl font-bold text-gradient-accent tabular-nums">{lead.lead_score}</p>
              </div>
              <span className="rounded-full border border-[color:var(--border-color)] bg-[color:var(--card-bg)] px-3 py-1 text-xs font-semibold text-[color:var(--text-primary)]">
                {priorityFromTier(lead.lead_tier)}
              </span>
            </div>
          </section>

          {/* B. Recommended action */}
          <section>
            <h4 className="text-sm font-semibold text-[color:var(--text-primary)] mb-2">Recommended action</h4>
            <div
              className={cn(
                "rounded-2xl border px-4 py-3 text-sm",
                "border-[color:var(--accent)]/40 bg-gradient-to-br from-[color:var(--accent-soft)] to-transparent",
                "text-[color:var(--text-primary)] shadow-[0_0_24px_rgba(99,102,241,0.15)]"
              )}
            >
              {lead.lead_tier === "hot"
                ? "Contact within 24 hours — strong fit and high intent."
                : lead.lead_tier === "warm"
                  ? "Reach out this week with a tailored value hook."
                  : "Add to nurture sequence; monitor hiring and news signals."}
            </div>
          </section>

          <div className="h-px bg-[color:var(--border-color)]" />

          {/* C. AI insights */}
          <section className="space-y-3">
            <h4 className="text-sm font-semibold text-[color:var(--text-primary)]">AI insights</h4>
            <div className="space-y-2 rounded-2xl border border-[color:var(--border-color)] bg-[color:var(--card-bg)]/80 p-4">
              <div className="flex justify-between text-sm">
                <span className="text-[color:var(--text-secondary)]">Hiring signal</span>
                <span className="font-medium text-[color:var(--text-primary)]">
                  {explain.hiringSignal ? "Active hiring" : "No strong signal"}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[color:var(--text-secondary)]">Industry match</span>
                <span className="font-medium text-[color:var(--text-primary)]">
                  {explain.industryPoints > 12 ? "Strong" : explain.industryPoints > 6 ? "Good" : "Building"}
                </span>
              </div>
            </div>
            <div className="space-y-3">
              {bars.map((b, i) => (
                <div key={b.id}>
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="text-[color:var(--text-secondary)]">{b.label}</span>
                    <span className="tabular-nums text-[color:var(--text-primary)]">
                      {b.points}/{b.max}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-[color:var(--border-color)]/70">
                    <div
                      className="h-full origin-left rounded-full bg-[image:var(--accent-gradient)] animate-bar"
                      style={{
                        animationDelay: `${i * 60}ms`,
                        transform: `scaleX(${b.max ? b.points / b.max : 0})`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="h-px bg-[color:var(--border-color)]" />

          {/* D. Outreach preview */}
          <section>
            <h4 className="text-sm font-semibold text-[color:var(--text-primary)] mb-2">Outreach preview</h4>
            <div
              className={cn(
                "rounded-2xl border border-[color:var(--border-color)] p-4",
                "bg-[color:var(--bg-secondary)]/80 font-mono text-sm leading-relaxed",
                "text-[color:var(--text-secondary)] whitespace-pre-wrap"
              )}
            >
              {outreach}
            </div>
          </section>
        </div>
      </aside>
    </>
  );
}
