"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LayoutGrid, Search, Table2 } from "lucide-react";
import { toast } from "sonner";

import type { Lead, LeadStats, User } from "@/lib/api";
import { emailFromLead } from "@/lib/lead-view";
import type { ParsedLeadsQuery } from "@/lib/leads-url";
import { stringifyLeadsQuery } from "@/lib/leads-url";
import { cn } from "@/lib/cn";

import { AiInsightsStrip } from "./ai-insights-strip";
import { LeadDrawer } from "./lead-drawer";
import { LeadIntelligenceHero } from "./lead-intelligence-hero";
import { LeadKanban } from "./lead-kanban";
import { LeadTableView } from "./lead-table-view";
import { StatsGlassRow } from "./stats-glass-row";

interface Props {
  user: User;
  initialLeads: Lead[];
  stats: LeadStats;
  query: ParsedLeadsQuery;
  total: number;
  pages: number;
}

/**
 * Lead Intelligence shell: hero, AI strip, stats, Kanban-first pipeline, AI drawer.
 */
export function LeadIntelligenceDashboard({
  user,
  initialLeads,
  stats,
  query,
  total,
  pages,
}: Props) {
  const [leads, setLeads] = useState<Lead[]>(initialLeads);
  const [activeLead, setActiveLead] = useState<Lead | null>(null);

  useEffect(() => {
    setLeads(initialLeads);
  }, [initialLeads]);

  const kanbanHref = `/dashboard/leads?${stringifyLeadsQuery({ ...query, view: "kanban" })}`;
  const tableHref = `/dashboard/leads?${stringifyLeadsQuery({ ...query, view: "table" })}`;

  function handleLeadUpdated(updated: Lead) {
    setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    setActiveLead((cur) => (cur?.id === updated.id ? updated : cur));
    toast.success("Pipeline updated");
  }

  function handleQuickContact(lead: Lead) {
    setActiveLead(lead);
    const email = emailFromLead(lead);
    if (email) {
      window.open(`mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent(`Hello from ${user.company_name ?? "Zentro"}`)}`);
      toast.message("Opening mail client");
    } else {
      toast.info("No verified email on file — open the brief to plan outreach.");
    }
  }

  const empty = total === 0;

  return (
    <div className="space-y-6 animate-fade-up">
      <LeadIntelligenceHero />
      <AiInsightsStrip />

      <StatsGlassRow stats={stats} leadsUsed={user.leads_used_this_month} leadsLimit={user.leads_limit} />

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="inline-flex rounded-xl border border-[color:var(--border-color)] bg-[color:var(--card-bg)] p-1 backdrop-blur-md">
          <Link
            href={kanbanHref}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all",
              query.view === "kanban"
                ? "bg-[image:var(--accent-gradient)] text-white shadow-md"
                : "text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)]"
            )}
          >
            <LayoutGrid className="h-4 w-4" />
            Pipeline
          </Link>
          <Link
            href={tableHref}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all",
              query.view === "table"
                ? "bg-[image:var(--accent-gradient)] text-white shadow-md"
                : "text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)]"
            )}
          >
            <Table2 className="h-4 w-4" />
            Table
          </Link>
        </div>

        <form
          className="flex w-full max-w-md items-center gap-2 rounded-xl border border-[color:var(--border-color)] bg-[color:var(--card-bg)] px-3 py-2 backdrop-blur-md sm:w-auto"
          action="/dashboard/leads"
          method="get"
        >
          <Search className="h-4 w-4 flex-shrink-0 text-[color:var(--text-muted)]" />
          <input type="hidden" name="view" value={query.view} />
          <input type="hidden" name="per_page" value={String(query.per_page)} />
          <input type="hidden" name="page" value="1" />
          {query.tier ? <input type="hidden" name="tier" value={query.tier} /> : null}
          {query.status ? <input type="hidden" name="status" value={query.status} /> : null}
          {query.has_email === true ? <input type="hidden" name="has_email" value="true" /> : null}
          {query.has_email === false ? <input type="hidden" name="has_email" value="false" /> : null}
          {query.zims_synced === true ? <input type="hidden" name="zims" value="true" /> : null}
          {query.zims_synced === false ? <input type="hidden" name="zims" value="false" /> : null}
          <input
            name="search"
            defaultValue={query.search ?? ""}
            placeholder="Search companies…"
            className="min-w-0 flex-1 bg-transparent text-sm text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)] outline-none"
          />
          <button
            type="submit"
            className="rounded-lg bg-[color:var(--accent-soft)] px-3 py-1 text-xs font-semibold text-[color:var(--accent)]"
          >
            Apply
          </button>
        </form>
      </div>

      {empty ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-[color:var(--border-color)] bg-[color:var(--accent-gradient-soft)] px-6 py-16 text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[image:var(--accent-gradient)] shadow-[var(--shadow-glow)]">
            <Search className="h-8 w-8 text-white opacity-90" />
          </div>
          <h3 className="text-lg font-semibold text-[color:var(--text-primary)]">No leads yet</h3>
          <p className="mt-2 max-w-md text-sm text-[color:var(--text-secondary)]">
            Define an ICP and generate your first batch — your AI pipeline will light up here.
          </p>
          <Link
            href="/dashboard/icp"
            className={cn(
              "mt-6 inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold text-white",
              "bg-[image:var(--accent-gradient)] shadow-lg transition hover:scale-[1.02] hover:shadow-[var(--shadow-glow)] btn-ripple"
            )}
          >
            Build ICP &amp; generate
          </Link>
        </div>
      ) : query.view === "kanban" ? (
        <LeadKanban
          leads={leads}
          onLeadUpdated={handleLeadUpdated}
          onView={setActiveLead}
          onQuickContact={handleQuickContact}
          onDragError={(msg) => toast.error(msg)}
        />
      ) : (
        <LeadTableView leads={leads} onRowClick={setActiveLead} />
      )}

      {!empty && query.view === "table" && pages > 1 ? (
        <div className="flex justify-center gap-2 pt-2">
          {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
            <Link
              key={p}
              href={`/dashboard/leads?${stringifyLeadsQuery({ ...query, page: p })}`}
              className={cn(
                "min-w-9 rounded-lg px-3 py-1.5 text-sm font-medium transition",
                p === query.page
                  ? "bg-[color:var(--accent-soft)] text-[color:var(--accent)]"
                  : "text-[color:var(--text-secondary)] hover:bg-[color:var(--accent-soft)]/50"
              )}
            >
              {p}
            </Link>
          ))}
        </div>
      ) : null}

      <LeadDrawer lead={activeLead} onClose={() => setActiveLead(null)} />
    </div>
  );
}
