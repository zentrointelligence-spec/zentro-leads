/**
 * View-model helpers for ZLIS lead dashboard (maps API Lead → flat row + “why” copy).
 */

import type { Company, Lead } from "@/lib/api";

export interface LeadRowView {
  id: string;
  companyName: string;
  industry: string | null;
  email: string | null;
  score: number;
  tier: string;
  status: string;
  notes: string | null;
  isSuppressed: boolean;
  zimsSynced: boolean;
  raw: Lead;
}

export function companyNameFromLead(lead: Lead): string {
  return lead.company?.name?.trim() || "—";
}

export function industryFromLead(lead: Lead): string | null {
  return lead.company?.industry ?? null;
}

export function emailFromLead(lead: Lead): string | null {
  return lead.person?.email ?? null;
}

export function toLeadRow(lead: Lead): LeadRowView {
  const status = lead.status as string;
  return {
    id: lead.id,
    companyName: companyNameFromLead(lead),
    industry: industryFromLead(lead),
    email: emailFromLead(lead),
    score: lead.lead_score,
    tier: lead.lead_tier,
    status,
    notes: lead.notes,
    isSuppressed: status === "suppressed",
    zimsSynced: Boolean(lead.zims_lead_id && lead.zims_lead_id.length > 0),
    raw: lead,
  };
}

export interface ScoreExplain {
  industryPoints: number;
  hiringSignal: boolean;
  signalsDetected: string[];
  breakdownLines: string[];
}

export interface ScoreBreakdownBar {
  id: string;
  label: string;
  points: number;
  max: number;
}

/**
 * Normalized score components for progress UI (max values follow product scoring caps).
 */
export function scoreBreakdownBars(lead: Lead): ScoreBreakdownBar[] {
  const b = (lead.score_breakdown || {}) as Record<string, unknown>;
  return [
    { id: "company_size", label: "Company size", points: Number(b.company_size ?? 0), max: 30 },
    { id: "role", label: "Role fit", points: Number(b.role ?? 0), max: 25 },
    { id: "industry", label: "Industry", points: Number(b.industry ?? 0), max: 20 },
    { id: "signals", label: "Intent signals", points: Number(b.signals ?? 0), max: 15 },
    { id: "email", label: "Email quality", points: Number(b.email ?? 0), max: 10 },
  ];
}

export function explainLead(lead: Lead, company: Company | null): ScoreExplain {
  const b = (lead.score_breakdown || {}) as Record<string, unknown>;
  const industryPoints = Number(b.industry ?? 0);
  const hiringSignal = Boolean(company?.is_hiring);
  const signalsDetected = Array.isArray(b.signals_detected)
    ? (b.signals_detected as string[])
    : Array.isArray(lead.intent_signals)
      ? lead.intent_signals
      : [];

  const breakdownLines: string[] = [
    `Company size match: +${Number(b.company_size ?? 0)}`,
    `Role match: +${Number(b.role ?? 0)}`,
    `Industry match: +${Number(b.industry ?? 0)}`,
    `Intent signals: +${Number(b.signals ?? 0)}`,
    `Email quality: +${Number(b.email ?? 0)}`,
  ];
  if (signalsDetected.length) {
    breakdownLines.push(`Detected: ${signalsDetected.join(", ")}`);
  }

  return {
    industryPoints,
    hiringSignal,
    signalsDetected,
    breakdownLines,
  };
}

export function tierBadgeClass(tier: string): string {
  const base =
    "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide";
  switch (tier) {
    case "hot":
      return `${base} border-red-500/20 bg-red-500/[0.08] text-red-400/95`;
    case "warm":
      return `${base} border-amber-500/20 bg-amber-500/[0.08] text-amber-300/95`;
    case "potential":
      return `${base} border-blue-500/25 bg-blue-500/[0.1] text-blue-300/95`;
    default:
      return `${base} border-white/[0.08] bg-white/[0.04] text-zinc-400`;
  }
}
