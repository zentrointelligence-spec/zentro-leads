"use client";

import { useEffect, useMemo, useTransition } from "react";
import { toast } from "sonner";
import { X, Copy, Ban, CloudUpload, CheckCircle2, XCircle } from "lucide-react";

import type { Lead } from "@/lib/api";
import {
  companyNameFromLead,
  emailFromLead,
  explainLead,
  industryFromLead,
  scoreBreakdownBars,
  tierBadgeClass,
} from "@/lib/lead-view";
import { MutedLabel, ProgressBar } from "./leads-primitives";
import { useLeadsDashboardActions } from "./leads-dashboard-context";

interface Props {
  lead: Lead | null;
  open: boolean;
  onClose: () => void;
}

const chip =
  "inline-flex items-center rounded-full border border-white/[0.08] bg-white/[0.03] px-2.5 py-1 text-[12px] font-medium text-zinc-300";

function SignalRow({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center justify-between gap-3 text-[13px]">
      <span className="text-zinc-400">{label}</span>
      <span className="flex shrink-0 items-center gap-1.5 font-medium text-zinc-200">
        {ok ? (
          <>
            <CheckCircle2 className="h-4 w-4 text-emerald-400/90" aria-hidden />
            <span className="text-emerald-300/95">Yes</span>
          </>
        ) : (
          <>
            <XCircle className="h-4 w-4 text-zinc-600" aria-hidden />
            <span className="text-zinc-500">No</span>
          </>
        )}
      </span>
    </div>
  );
}

/**
 * Right-hand detail drawer with “Why this lead?” and outreach copy actions.
 */
export function LeadDrawer({ lead, open, onClose }: Props) {
  const [pending, startTransition] = useTransition();
  const { suppressLeadOptimistic, syncZimsOptimistic } = useLeadsDashboardActions();

  const explain = useMemo(
    () => (lead ? explainLead(lead, lead.company ?? null) : null),
    [lead]
  );
  const bars = useMemo(() => (lead ? scoreBreakdownBars(lead) : []), [lead]);

  const insightLines = useMemo(() => {
    if (!explain) return [];
    const lines: string[] = [];
    if (explain.industryPoints >= 12) lines.push("Strong industry match");
    else if (explain.industryPoints > 0) lines.push("Partial industry match");
    if (explain.hiringSignal) lines.push("High hiring intent");
    if (explain.signalsDetected.length) lines.push("Active intent signals");
    return lines;
  }, [explain]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open || !lead || !explain) return null;

  const emailConf = lead.person?.email_confidence ?? 0;

  function copy(text: string | null | undefined, label: string) {
    if (!text) {
      toast.error("Nothing to copy.");
      return;
    }
    void navigator.clipboard.writeText(text);
    toast.success(`${label} copied.`);
  }

  return (
    <>
      <button
        type="button"
        aria-label="Close drawer"
        className="fixed inset-0 z-40 bg-zinc-950/55 backdrop-blur-[2px] transition-opacity duration-200 ease-out"
        onClick={onClose}
      />
      <aside className="fixed inset-0 z-50 flex w-full flex-col border-white/[0.06] bg-[#09090b] shadow-2xl shadow-black/40 sm:inset-y-0 sm:left-auto sm:right-0 sm:h-full sm:max-w-lg sm:border-l">
        <div className="flex items-start justify-between gap-4 border-b border-white/[0.06] px-5 py-5 sm:px-6">
          <div className="min-w-0 flex-1">
            <MutedLabel>Lead</MutedLabel>
            <h3 className="mt-2 truncate text-xl font-semibold tracking-tight text-zinc-100">
              {companyNameFromLead(lead)}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-md p-2 text-zinc-500 transition-colors duration-150 hover:bg-white/[0.06] hover:text-zinc-200 active:scale-95"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 space-y-8 overflow-y-auto px-5 py-6 sm:px-6">
          <div className="flex flex-wrap gap-2">
            <span className={tierBadgeClass(lead.lead_tier)}>{lead.lead_tier}</span>
            <span className={chip}>Score {lead.lead_score}</span>
            <span className={`${chip} capitalize`}>{lead.status}</span>
          </div>

          <dl className="grid gap-5 text-[13px]">
            <div>
              <MutedLabel className="mb-2 block">Industry</MutedLabel>
              <dd className="font-medium text-zinc-200">{industryFromLead(lead) || "—"}</dd>
            </div>
            <div>
              <MutedLabel className="mb-2 block">Email</MutedLabel>
              <dd className="break-all font-medium text-zinc-200">{emailFromLead(lead) || "—"}</dd>
            </div>
            <div>
              <MutedLabel className="mb-2 block">Person</MutedLabel>
              <dd className="font-medium text-zinc-200">
                {lead.person?.full_name || "—"}
                {lead.person?.job_title ? (
                  <span className="font-normal text-zinc-500"> · {lead.person.job_title}</span>
                ) : null}
              </dd>
            </div>
            <div>
              <MutedLabel className="mb-2 block">ZIMS</MutedLabel>
              <dd className="font-medium text-zinc-200">
                {lead.zims_lead_id ? `Synced (${lead.zims_lead_id})` : "Not synced"}
              </dd>
            </div>
          </dl>

          <section className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-5 shadow-sm">
            <MutedLabel className="mb-4 block">Why this lead?</MutedLabel>
            <div className="space-y-3">
              <SignalRow ok={explain.industryPoints > 0} label="Industry match" />
              <SignalRow ok={explain.hiringSignal} label="Hiring signal" />
              <div>
                <div className="mb-2 flex items-center justify-between text-[12px] text-zinc-500">
                  <span>Email confidence</span>
                  <span className="tabular-nums text-zinc-300">{emailConf}%</span>
                </div>
                <ProgressBar value={emailConf} max={100} barClassName="from-emerald-500/90 to-emerald-400/80" />
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between text-[12px] text-zinc-500">
                  <span>Lead score</span>
                  <span className="tabular-nums text-zinc-300">{lead.lead_score} / 100</span>
                </div>
                <ProgressBar value={lead.lead_score} max={100} />
              </div>
            </div>
            {insightLines.length ? (
              <ul className="mt-4 space-y-1.5 border-t border-white/[0.06] pt-4 text-[12px] font-medium text-zinc-300">
                {insightLines.map((line) => (
                  <li key={line}>· {line}</li>
                ))}
              </ul>
            ) : null}
            <div className="mt-4 space-y-3 border-t border-white/[0.06] pt-4">
              <MutedLabel className="mb-2 block">Score breakdown</MutedLabel>
              {bars.map((b) => (
                <div key={b.id}>
                  <div className="mb-1 flex items-center justify-between text-[11px] text-zinc-500">
                    <span>{b.label}</span>
                    <span className="tabular-nums text-zinc-400">
                      {b.points} / {b.max}
                    </span>
                  </div>
                  <ProgressBar value={b.points} max={b.max} barClassName="from-sky-500/90 to-brand-blue/90" />
                </div>
              ))}
            </div>
          </section>

          <section>
            <MutedLabel className="mb-3 block">Notes</MutedLabel>
            <p className="min-h-[88px] whitespace-pre-wrap rounded-md border border-white/[0.06] bg-[#08080a] p-4 text-[13px] leading-relaxed text-zinc-400 shadow-sm">
              {lead.notes || "—"}
            </p>
          </section>

          <section className="space-y-3">
            <MutedLabel>AI outreach</MutedLabel>
            {lead.ai_whatsapp_msg ? (
              <div className="space-y-4 rounded-lg border border-white/[0.06] bg-[#08080a] p-4 text-[13px] leading-relaxed text-zinc-400 shadow-sm">
                <div>
                  <MutedLabel className="mb-2 block">WhatsApp</MutedLabel>
                  <p className="text-zinc-300">{lead.ai_whatsapp_msg}</p>
                  <button
                    type="button"
                    onClick={() => copy(lead.ai_whatsapp_msg, "WhatsApp message")}
                    className="mt-3 inline-flex items-center gap-1.5 text-[12px] font-medium text-brand-blue transition-colors hover:text-brand-blue-dark active:scale-[0.98]"
                  >
                    <Copy className="h-3.5 w-3.5 opacity-80" /> Copy
                  </button>
                </div>
                {lead.ai_email_subject ? (
                  <div>
                    <MutedLabel className="mb-2 block">Email subject</MutedLabel>
                    <p className="text-zinc-300">{lead.ai_email_subject}</p>
                  </div>
                ) : null}
                {lead.ai_email_body ? (
                  <div>
                    <MutedLabel className="mb-2 block">Email body</MutedLabel>
                    <p className="whitespace-pre-wrap text-zinc-300">{lead.ai_email_body}</p>
                  </div>
                ) : null}
                {lead.ai_linkedin_note ? (
                  <div>
                    <MutedLabel className="mb-2 block">LinkedIn</MutedLabel>
                    <p className="text-zinc-300">{lead.ai_linkedin_note}</p>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="text-[13px] text-zinc-600">No AI outreach generated for this lead yet.</p>
            )}
          </section>
        </div>

        <div className="flex flex-wrap gap-2 border-t border-white/[0.06] px-5 py-5 sm:px-6">
          <button
            type="button"
            disabled={pending}
            onClick={() =>
              startTransition(async () => {
                const ok = await suppressLeadOptimistic(lead);
                if (ok) onClose();
              })
            }
            className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-md border border-red-500/25 bg-red-500/[0.08] px-4 text-[13px] font-medium text-red-200/95 transition-[border-color,background-color,transform] duration-150 hover:border-red-500/40 hover:bg-red-500/[0.12] active:scale-[0.99] disabled:pointer-events-none disabled:opacity-40 sm:flex-none"
          >
            <Ban className="h-4 w-4 opacity-90" />
            Suppress
          </button>
          <button
            type="button"
            disabled={pending}
            onClick={() =>
              startTransition(async () => {
                await syncZimsOptimistic(lead);
              })
            }
            className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-md bg-brand-blue px-4 text-[13px] font-medium text-white shadow-md transition-[background-color,transform,opacity] duration-150 ease-out hover:bg-brand-blue-dark active:scale-[0.99] disabled:pointer-events-none disabled:opacity-40 sm:flex-none sm:min-w-[140px]"
          >
            <CloudUpload className="h-4 w-4 opacity-90" />
            Sync to ZIMS
          </button>
        </div>
      </aside>
    </>
  );
}

export default LeadDrawer;
