"use client";

import { memo, useState } from "react";
import { Ban, Building2, Eye, Gauge, Mail } from "lucide-react";

import type { Lead } from "@/lib/api";
import {
  companyNameFromLead,
  emailFromLead,
  industryFromLead,
  tierBadgeClass,
} from "@/lib/lead-view";
import { cn } from "@/lib/cn";

import { useLeadsDashboardActions } from "./leads-dashboard-context";

interface Props {
  lead: Lead;
  onOpen: (lead: Lead) => void;
}

/**
 * Compact pipeline card for Kanban columns.
 */
export const LeadCard = memo(function LeadCard({ lead, onOpen }: Props) {
  const { suppressLeadOptimistic } = useLeadsDashboardActions();
  const [busy, setBusy] = useState(false);
  const email = emailFromLead(lead);
  const verified = lead.person?.email_verified;

  return (
    <div className="group/card relative">
      <div
        role="button"
        tabIndex={0}
        onClick={() => onOpen(lead)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onOpen(lead);
          }
        }}
        className="w-full cursor-pointer rounded-md border border-white/[0.06] bg-[#08080a]/90 px-3.5 py-3 text-left outline-none shadow-sm transition-[border-color,background-color,box-shadow,transform] duration-200 ease-out hover:-translate-y-0.5 hover:border-white/[0.1] hover:bg-[#0c0c0f] hover:shadow-md focus-visible:ring-2 focus-visible:ring-brand-blue/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[#08080a]"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="flex items-center gap-2 truncate text-[13px] font-medium tracking-tight text-zinc-100">
              <Building2 className="h-3.5 w-3.5 shrink-0 text-zinc-600" />
              {companyNameFromLead(lead)}
            </p>
            <p className="mt-1 truncate text-[12px] leading-snug text-zinc-500">
              {industryFromLead(lead) || "—"}
            </p>
          </div>
          <span className={cn("shrink-0", tierBadgeClass(lead.lead_tier))}>{lead.lead_tier}</span>
        </div>
        <div className="mt-3 flex items-center justify-between text-[12px] text-zinc-500">
          <span className="inline-flex items-center gap-1.5 tabular-nums text-zinc-400">
            <Gauge className="h-3.5 w-3.5 text-zinc-600" />
            {lead.lead_score}
          </span>
          <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-zinc-500">
            <Mail className="h-3.5 w-3.5 text-zinc-600" />
            {email ? (verified ? "Verified" : "Unverified") : "No email"}
          </span>
        </div>
      </div>

      <div className="pointer-events-none absolute right-2 top-2 flex gap-1 opacity-0 transition-opacity duration-150 group-hover/card:pointer-events-auto group-hover/card:opacity-100">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onOpen(lead);
          }}
          className="pointer-events-auto rounded-md border border-white/[0.1] bg-[#09090b]/95 p-1.5 text-zinc-300 shadow-md backdrop-blur-sm transition-[transform,colors] hover:text-white active:scale-95"
          aria-label="View lead"
        >
          <Eye className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={(e) => {
            e.stopPropagation();
            void (async () => {
              setBusy(true);
              try {
                await suppressLeadOptimistic(lead);
              } finally {
                setBusy(false);
              }
            })();
          }}
          className="pointer-events-auto rounded-md border border-red-500/30 bg-[#09090b]/95 p-1.5 text-red-300 shadow-md backdrop-blur-sm transition-[transform,colors] hover:bg-red-500/15 active:scale-95 disabled:opacity-40"
          aria-label="Suppress lead"
        >
          <Ban className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
});
