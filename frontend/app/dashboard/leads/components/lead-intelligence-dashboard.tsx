"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { LayoutGrid, Table2, Download, Plus, Search, Flame, Zap, TrendingUp, Snowflake, ChevronDown, Mail, X, Loader2 } from "lucide-react";
import { toast } from "sonner";

import type { Lead, LeadStats, User } from "@/lib/api";
import { emailFromLead } from "@/lib/lead-view";
import type { ParsedLeadsQuery } from "@/lib/leads-url";
import { stringifyLeadsQuery } from "@/lib/leads-url";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";

import { LeadDrawer } from "./lead-drawer";
import { LeadKanban } from "./lead-kanban";
import { LeadTableView } from "./lead-table-view";

interface Props {
  user: User;
  initialLeads: Lead[];
  stats: LeadStats;
  query: ParsedLeadsQuery;
  total: number;
  pages: number;
}

const STATUS_FILTERS = [
  { key: undefined, label: "All" },
  { key: "new", label: "New" },
  { key: "contacted", label: "Contacted" },
  { key: "replied", label: "Replied" },
  { key: "meeting", label: "Meeting" },
  { key: "closed", label: "Closed" },
  { key: "lost", label: "Lost" },
] as const;

const STAT_PILLS = [
  { key: "hot", label: "HOT", icon: Flame, color: "var(--color-hot)", bg: "var(--color-hot-bg)", border: "var(--color-hot-border)" },
  { key: "warm", label: "WARM", icon: Zap, color: "var(--color-warm)", bg: "var(--color-warm-bg)", border: "var(--color-warm-border)" },
  { key: "potential", label: "POTENTIAL", icon: TrendingUp, color: "var(--color-potential)", bg: "var(--color-potential-bg)", border: "var(--color-potential-border)" },
  { key: "cold", label: "COLD", icon: Snowflake, color: "var(--color-cold)", bg: "var(--color-cold-bg)", border: "var(--color-cold-border)" },
];

interface FilterDef {
  label: string;
  param: string;
  options: { label: string; value: string }[];
}

const FILTERS: FilterDef[] = [
  {
    label: "Source",
    param: "source",
    options: [
      { label: "Google Maps", value: "google_maps" },
      { label: "Google Search", value: "google_search" },
      { label: "Website", value: "website" },
      { label: "LinkedIn", value: "linkedin" },
      { label: "Job Board", value: "job_board" },
      { label: "Manual", value: "manual" },
      { label: "Landing Page", value: "landing_page" },
    ],
  },
  {
    label: "Score",
    param: "score_range",
    options: [
      { label: "0 – 50", value: "0,50" },
      { label: "50 – 70", value: "50,70" },
      { label: "70 – 85", value: "70,85" },
      { label: "85 – 100", value: "85,100" },
    ],
  },
  {
    label: "ICP Match",
    param: "icp_range",
    options: [
      { label: "70%+", value: "70,100" },
      { label: "40 – 70%", value: "40,70" },
      { label: "Below 40%", value: "0,40" },
    ],
  },
  {
    label: "Tier",
    param: "tier",
    options: [
      { label: "Hot", value: "hot" },
      { label: "Warm", value: "warm" },
      { label: "Potential", value: "potential" },
      { label: "Cold", value: "cold" },
    ],
  },
  {
    label: "Location",
    param: "city",
    options: [
      { label: "Kuala Lumpur", value: "Kuala Lumpur" },
      { label: "Petaling Jaya", value: "Petaling Jaya" },
      { label: "Shah Alam", value: "Shah Alam" },
      { label: "Johor Bahru", value: "Johor Bahru" },
      { label: "Penang", value: "Penang" },
      { label: "Ipoh", value: "Ipoh" },
    ],
  },
];

function FilterDropdown({ filter }: { filter: FilterDef }) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const ref = useRef<HTMLDivElement>(null);

  const currentValue = searchParams.get(filter.param);
  const activeLabel = currentValue
    ? filter.options.find((o) => o.value === currentValue)?.label ?? currentValue
    : undefined;

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  function apply(value: string | undefined) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(filter.param, value);
    else params.delete(filter.param);
    // reset to page 1 on filter change
    params.set("page", "1");
    router.push(`${pathname}?${params.toString()}`);
    setOpen(false);
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors"
        style={{
          backgroundColor: activeLabel ? "var(--color-brand-bg)" : "var(--bg-card)",
          border: `1px solid ${activeLabel ? "var(--color-brand-border)" : "var(--border-primary)"}`,
          color: activeLabel ? "var(--color-brand)" : "var(--text-secondary)",
        }}
      >
        {activeLabel ? `${filter.label}: ${activeLabel}` : filter.label}
        {activeLabel ? (
          <span
            onClick={(e) => {
              e.stopPropagation();
              apply(undefined);
            }}
          >
            <X className="h-3 w-3" />
          </span>
        ) : (
          <ChevronDown className={cn("h-3 w-3 transition-transform", open && "rotate-180")} style={{ color: "var(--text-tertiary)" }} />
        )}
      </button>

      {open && (
        <div
          className="absolute left-0 top-full z-20 mt-1.5 w-44 rounded-xl p-1.5 shadow-lg"
          style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)" }}
        >
          <button
            onClick={() => apply(undefined)}
            className="flex w-full items-center rounded-lg px-3 py-2 text-xs transition-colors hover:bg-hover"
            style={{ color: "var(--text-secondary)" }}
          >
            All
          </button>
          {filter.options.map((opt) => (
            <button
              key={opt.value}
              onClick={() => apply(opt.value)}
              className="flex w-full items-center rounded-lg px-3 py-2 text-xs transition-colors hover:bg-hover"
              style={{ color: currentValue === opt.value ? "var(--color-brand)" : "var(--text-secondary)" }}
            >
              {opt.label}
              {currentValue === opt.value && <span className="ml-auto text-[10px]">●</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function LeadIntelligenceDashboard({
  user,
  initialLeads,
  stats,
  query,
  total,
  pages,
}: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [leads, setLeads] = useState<Lead[]>(initialLeads);
  const [activeLead, setActiveLead] = useState<Lead | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    setLeads(initialLeads);
  }, [initialLeads]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") router.refresh();
    }, 15000);
    return () => window.clearInterval(intervalId);
  }, [router]);

  const handleLeadUpdated = useCallback((updated: Lead) => {
    setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    setActiveLead((cur) => (cur?.id === updated.id ? updated : cur));
    toast.success("Pipeline updated");
  }, []);

  const handleQuickContact = useCallback((lead: Lead) => {
    setActiveLead(lead);
    const email = emailFromLead(lead);
    if (email) {
      window.open(`mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent(`Hello from ${user.company_name ?? "LeadRadar"}`)}`);
      toast.message("Opening mail client");
    } else {
      toast.info("No verified email on file");
    }
  }, [user.company_name]);

  async function handleExport() {
    setExporting(true);
    try {
      const response = await fetch("/api/v1/leads/export/csv", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          format: "csv",
        }),
      });

      if (!response.ok) {
        throw new Error("Export failed");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `leads-${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Leads exported successfully");
    } catch {
      toast.error("Export failed — try again");
    } finally {
      setExporting(false);
    }
  }

  function buildStatusHref(status: string | undefined) {
    const params = new URLSearchParams(searchParams.toString());
    if (status) params.set("status", status);
    else params.delete("status");
    params.set("view", query.view);
    return `${pathname}?${params.toString()}`;
  }

  function buildTierHref(tier: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (query.tier === tier) params.delete("tier");
    else params.set("tier", tier);
    params.set("view", query.view);
    return `${pathname}?${params.toString()}`;
  }

  const empty = total === 0;
  const kanbanHref = `/dashboard/leads?${stringifyLeadsQuery({ ...query, view: "kanban" })}`;
  const tableHref = `/dashboard/leads?${stringifyLeadsQuery({ ...query, view: "table" })}`;

  return (
    <div className="space-y-5 animate-fade-in-up">
      {/* Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>Leads</h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--text-secondary)" }}>{total} total leads</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="inline-flex rounded-lg p-0.5" style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)" }}>
            <Link
              href={tableHref}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                query.view === "table" ? "font-semibold" : ""
              )}
              style={query.view === "table" ? { backgroundColor: "var(--bg-hover)", color: "var(--text-primary)" } : { color: "var(--text-tertiary)" }}
            >
              <Table2 className="h-3.5 w-3.5" /> Table
            </Link>
            <Link
              href={kanbanHref}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                query.view === "kanban" ? "font-semibold" : ""
              )}
              style={query.view === "kanban" ? { backgroundColor: "var(--bg-hover)", color: "var(--text-primary)" } : { color: "var(--text-tertiary)" }}
            >
              <LayoutGrid className="h-3.5 w-3.5" /> Kanban
            </Link>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            disabled={exporting}
            leftIcon={exporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
          >
            Export
          </Button>
          <Link href="/dashboard/icp">
            <Button size="sm" leftIcon={<Plus className="h-3.5 w-3.5" />}>Generate Leads</Button>
          </Link>
        </div>
      </div>

      {/* Stat Pills */}
      <div className="flex flex-wrap gap-2">
        {STAT_PILLS.map((pill) => {
          const count = stats[pill.key as keyof LeadStats] as number;
          const active = query.tier === pill.key;
          return (
            <button
              key={pill.key}
              onClick={() => router.push(buildTierHref(pill.key))}
              className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium transition-all"
              style={
                active
                  ? { backgroundColor: pill.bg, border: `1px solid ${pill.color}`, color: pill.color }
                  : { backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)", color: "var(--text-secondary)" }
              }
            >
              <pill.icon className="h-3.5 w-3.5" />
              <span className="uppercase tracking-wide">{pill.label}</span>
              <span className="font-bold">{count}</span>
            </button>
          );
        })}
      </div>

      {/* Filters */}
      <div className="space-y-3">
        {/* Status pills */}
        <div className="flex flex-wrap items-center gap-1.5">
          {STATUS_FILTERS.map((s) => {
            const isActive = query.status === s.key || (!query.status && !s.key);
            return (
              <Link
                key={s.label}
                href={buildStatusHref(s.key)}
                className="rounded-full px-3.5 py-1.5 text-xs font-medium transition-all"
                style={
                  isActive
                    ? { backgroundColor: "var(--color-brand-bg)", color: "var(--color-brand)", border: "1px solid var(--color-brand-border)" }
                    : { color: "var(--text-tertiary)", border: "1px solid transparent" }
                }
              >
                {s.label}
              </Link>
            );
          })}
        </div>

        {/* Dropdowns */}
        <div className="flex flex-wrap items-center gap-2">
          {FILTERS.map((f) => (
            <FilterDropdown key={f.param} filter={f} />
          ))}
        </div>

        {/* Search */}
        <form
          className="flex items-center gap-2 rounded-lg px-3.5 py-2.5"
          style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)" }}
          action="/dashboard/leads"
          method="get"
        >
          <Search className="h-4 w-4 flex-shrink-0" style={{ color: "var(--text-tertiary)" }} />
          <input type="hidden" name="view" value={query.view} />
          <input type="hidden" name="per_page" value={String(query.per_page)} />
          <input type="hidden" name="page" value="1" />
          {query.tier ? <input type="hidden" name="tier" value={query.tier} /> : null}
          {query.status ? <input type="hidden" name="status" value={query.status} /> : null}
          {query.has_email === true ? <input type="hidden" name="has_email" value="true" /> : null}
          {query.has_email === false ? <input type="hidden" name="has_email" value="false" /> : null}
          {query.zims_synced === true ? <input type="hidden" name="zims" value="true" /> : null}
          {query.zims_synced === false ? <input type="hidden" name="zims" value="false" /> : null}
          {query.min_icp_match === 0 ? <input type="hidden" name="icp_min" value="0" /> : null}
          <input
            name="search"
            defaultValue={query.search ?? ""}
            placeholder="Search companies..."
            className="min-w-0 flex-1 bg-transparent text-sm outline-none"
            style={{ color: "var(--text-primary)" }}
          />
        </form>
      </div>

      {/* Content */}
      {empty ? (
        <div className="flex flex-col items-center justify-center rounded-xl py-20" style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)" }}>
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full" style={{ backgroundColor: "var(--color-brand-bg)" }}>
            <Mail className="h-6 w-6" style={{ color: "var(--color-brand)" }} />
          </div>
          <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>No leads found</h3>
          <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>Try adjusting your filters or generate new leads</p>
          <Link href="/dashboard/icp">
            <Button className="mt-5" size="sm" leftIcon={<Plus className="h-4 w-4" />}>Generate Leads</Button>
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

      {/* Pagination */}
      {!empty && query.view === "table" && pages > 1 && (
        <div className="flex justify-center gap-2 pt-2">
          {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
            <Link
              key={p}
              href={`/dashboard/leads?${stringifyLeadsQuery({ ...query, page: p })}`}
              className="min-w-9 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors"
              style={
                p === query.page
                  ? { backgroundColor: "var(--color-brand)", color: "#ffffff" }
                  : { backgroundColor: "var(--bg-card)", color: "var(--text-secondary)", border: "1px solid var(--border-primary)" }
              }
            >
              {p}
            </Link>
          ))}
        </div>
      )}

      <LeadDrawer
        lead={activeLead}
        onClose={() => setActiveLead(null)}
        onLeadUpdated={handleLeadUpdated}
        onLeadSuppressed={(id) => {
          setLeads((prev) => prev.filter((l) => l.id !== id));
          setActiveLead(null);
          toast.success("Lead removed from pipeline");
        }}
      />
    </div>
  );
}
