"use client";

import type { Lead } from "@/lib/api";
import { companyNameFromLead } from "@/lib/lead-view";
import { cn } from "@/lib/cn";

interface Props {
  leads: Lead[];
  onRowClick: (lead: Lead) => void;
}

/**
 * Dense table view — opens the same AI drawer on row click.
 */
export function LeadTableView({ leads, onRowClick }: Props) {
  const visible = leads.filter((l) => l.status !== "suppressed");

  if (visible.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-[color:var(--border-color)] bg-[color:var(--card-bg)] backdrop-blur-xl">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-[color:var(--border-color)] bg-[color:var(--bg-secondary)]/60">
            <th className="px-4 py-3 font-semibold text-[color:var(--text-secondary)]">Company</th>
            <th className="px-4 py-3 font-semibold text-[color:var(--text-secondary)]">Score</th>
            <th className="px-4 py-3 font-semibold text-[color:var(--text-secondary)]">Tier</th>
            <th className="px-4 py-3 font-semibold text-[color:var(--text-secondary)]">Status</th>
            <th className="px-4 py-3 font-semibold text-[color:var(--text-secondary)]">Contact</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((lead) => (
            <tr
              key={lead.id}
              onClick={() => onRowClick(lead)}
              className={cn(
                "cursor-pointer border-b border-[color:var(--border-color)]/60 transition-colors",
                "hover:bg-[color:var(--accent-soft)]/40"
              )}
            >
              <td className="px-4 py-3 font-medium text-[color:var(--text-primary)]">
                {companyNameFromLead(lead)}
              </td>
              <td className="px-4 py-3 tabular-nums text-[color:var(--text-primary)]">{lead.lead_score}</td>
              <td className="px-4 py-3 uppercase text-xs text-[color:var(--text-secondary)]">
                {lead.lead_tier}
              </td>
              <td className="px-4 py-3 text-[color:var(--text-secondary)]">{lead.status}</td>
              <td className="px-4 py-3 text-[color:var(--text-secondary)]">
                {lead.person?.email ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
