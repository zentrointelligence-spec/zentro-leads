"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useMemo, useState, useTransition, useCallback, memo } from "react";
import { usePathname, useRouter } from "next/navigation";
import { LayoutGrid, Sparkles, Table2 } from "lucide-react";

import type { Lead, PaginatedLeads } from "@/lib/api";
import type { ParsedLeadsQuery } from "@/lib/leads-url";
import { stringifyLeadsQuery } from "@/lib/leads-url";
import { cn } from "@/lib/cn";

import { LeadFilters } from "./LeadFilters";
import { LeadKanban } from "./LeadKanban";
import { LeadTable } from "./LeadTable";
import { NLSearchBar } from "./NLSearchBar";
import { LeadsDashboardProvider, useLeadsDashboardActions } from "./leads-dashboard-context";

const LeadDrawerLazy = dynamic(() => import("./LeadDrawer"), {
  ssr: false,
  loading: () => (
    <div
      className="fixed inset-0 z-50 bg-[#09090b]/85 backdrop-blur-sm sm:inset-y-0 sm:left-auto sm:right-0 sm:w-full sm:max-w-lg sm:border-l sm:border-white/[0.06]"
      aria-hidden
    />
  ),
});

interface Props {
  initialQuery: ParsedLeadsQuery;
  paginated: PaginatedLeads;
}

const LeadDrawerGate = memo(function LeadDrawerGate({
  selected,
  onClose,
}: {
  selected: Lead | null;
  onClose: () => void;
}) {
  const { pipelineLeads } = useLeadsDashboardActions();
  const resolved = useMemo(
    () => (selected ? pipelineLeads.find((l) => l.id === selected.id) ?? selected : null),
    [pipelineLeads, selected]
  );

  if (!selected) return null;

  return <LeadDrawerLazy lead={resolved} open onClose={onClose} />;
});

/**
 * Client shell for ZLIS leads: AI search, URL filters, table vs Kanban, and detail drawer.
 */
export function LeadsDashboard({ initialQuery, paginated }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [nlResults, setNlResults] = useState<Lead[] | null>(null);
  const [selected, setSelected] = useState<Lead | null>(null);
  const [isNavigating, startNavTransition] = useTransition();

  const displayLeads = useMemo(
    () => nlResults ?? paginated.items,
    [nlResults, paginated.items]
  );

  const view = initialQuery.view;

  const setView = useCallback(
    (next: ParsedLeadsQuery["view"]) => {
      const qs = stringifyLeadsQuery({ ...initialQuery, view: next, page: 1 });
      startNavTransition(() => {
        router.push(`${pathname}?${qs}`);
        router.refresh();
      });
    },
    [router, pathname, initialQuery]
  );

  const onPageChange = useCallback(
    (page: number) => {
      const qs = stringifyLeadsQuery({ ...initialQuery, page });
      startNavTransition(() => {
        router.push(`${pathname}?${qs}`);
        router.refresh();
      });
    },
    [router, pathname, initialQuery]
  );

  const emptyNl = nlResults !== null && nlResults.length === 0;
  const emptyAll = displayLeads.length === 0;

  return (
    <LeadsDashboardProvider
      displayLeads={displayLeads}
      onLeadSuppressed={(id) => setSelected((s) => (s?.id === id ? null : s))}
    >
      <div className="space-y-8">
        <header className="flex flex-col gap-4 border-b border-white/[0.06] pb-8 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-2xl space-y-2">
            <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-zinc-500">
              Zentro Leads Intelligence System
            </p>
            <h1 className="text-xl font-semibold tracking-tight text-zinc-100 sm:text-2xl">
              Lead Intelligence
            </h1>
            <p className="text-sm leading-relaxed text-zinc-500 sm:text-[15px]">
              AI-powered lead generation and scoring — filter, search, and sync your best accounts
              to ZIMS.
            </p>
          </div>
          <Link
            href="/dashboard/icp"
            className="inline-flex h-11 shrink-0 items-center justify-center gap-2 self-start rounded-md bg-brand-blue px-5 text-[13px] font-semibold text-white shadow-md transition-[background-color,transform,box-shadow] duration-150 hover:bg-brand-blue-dark active:scale-[0.98]"
          >
            <Sparkles className="h-4 w-4 opacity-90" />
            Generate leads
          </Link>
        </header>

        <NLSearchBar
          onResults={(items) => setNlResults(items)}
          onClear={() => setNlResults(null)}
        />

        <LeadFilters initial={initialQuery} />

        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div
            className="inline-flex w-fit rounded-md border border-white/[0.06] bg-[#09090b]/80 p-0.5 shadow-md shadow-black/25"
            role="tablist"
            aria-label="View mode"
          >
            <ViewToggle
              active={view === "table"}
              onClick={() => setView("table")}
              icon={Table2}
              label="Table"
            />
            <ViewToggle
              active={view === "kanban"}
              onClick={() => setView("kanban")}
              icon={LayoutGrid}
              label="Kanban"
            />
          </div>
          {nlResults ? (
            <p className="text-[12px] leading-snug text-zinc-500">
              <span className="font-medium text-zinc-300">{nlResults.length}</span> AI-matched
              lead{nlResults.length === 1 ? "" : "s"} · replaces the current page view
            </p>
          ) : (
            <p className="text-[12px] tabular-nums text-zinc-500">
              Page <span className="text-zinc-300">{paginated.page}</span> of{" "}
              <span className="text-zinc-300">{Math.max(1, paginated.pages)}</span>
              <span className="mx-2 text-zinc-700">·</span>
              <span className="text-zinc-300">{paginated.total}</span> total
            </p>
          )}
        </div>

        <LeadsBody
          emptyAll={emptyAll}
          emptyNl={emptyNl}
          view={view}
          paginated={paginated}
          nlResults={nlResults}
          isNavigating={isNavigating}
          onPageChange={onPageChange}
          onView={setSelected}
        />

        <LeadDrawerGate selected={selected} onClose={() => setSelected(null)} />
      </div>
    </LeadsDashboardProvider>
  );
}

function LeadsBody({
  emptyAll,
  emptyNl,
  view,
  paginated,
  nlResults,
  isNavigating,
  onPageChange,
  onView,
}: {
  emptyAll: boolean;
  emptyNl: boolean;
  view: ParsedLeadsQuery["view"];
  paginated: PaginatedLeads;
  nlResults: Lead[] | null;
  isNavigating: boolean;
  onPageChange: (page: number) => void;
  onView: (lead: Lead) => void;
}) {
  const { pipelineLeads } = useLeadsDashboardActions();
  const manualNl = Boolean(nlResults);

  if (emptyAll) {
    return <EmptyState emptyNl={emptyNl} />;
  }

  if (pipelineLeads.length === 0) {
    return (
      <div className="animate-leads-fade-in rounded-lg border border-white/[0.06] bg-[#09090b]/50 py-16 text-center text-[13px] text-zinc-500 shadow-md">
        Updating your workspace…
      </div>
    );
  }

  return (
    <div className="animate-leads-fade-in">
      {view === "table" ? (
        <LeadTable
          leads={pipelineLeads}
          paginated={paginated}
          manualFromNl={manualNl}
          onPageChange={onPageChange}
          onView={onView}
          isNavigating={isNavigating}
        />
      ) : (
        <LeadKanban leads={pipelineLeads} onOpen={onView} />
      )}
    </div>
  );
}

function ViewToggle({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: typeof Table2;
  label: string;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 rounded-[6px] px-3 py-1.5 text-[13px] font-medium transition-[color,background-color,box-shadow,transform] duration-150 ease-out active:scale-[0.98]",
        active
          ? "bg-zinc-800 text-zinc-100 shadow-md shadow-black/25"
          : "text-zinc-500 hover:bg-white/[0.04] hover:text-zinc-300"
      )}
    >
      <Icon className="h-3.5 w-3.5 opacity-80" />
      {label}
    </button>
  );
}

function EmptyState({ emptyNl }: { emptyNl: boolean }) {
  return (
    <div className="rounded-lg border border-dashed border-white/[0.08] bg-[#09090b]/40 px-8 py-20 text-center shadow-md transition-colors duration-200 hover:border-white/[0.12]">
      <p className="text-[15px] font-medium tracking-tight text-zinc-100">
        {emptyNl ? "Try a different query" : "No leads yet. Generate leads to get started."}
      </p>
      <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-zinc-500">
        {emptyNl
          ? "Rephrase your AI prompt or clear AI search to return to your filtered list."
          : "Create an ICP and generate leads, or run an AI search to fill this workspace."}
      </p>
    </div>
  );
}
