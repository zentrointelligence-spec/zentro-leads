"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import { Filter, Search, X } from "lucide-react";

import type { ParsedLeadsQuery } from "@/lib/leads-url";
import { stringifyLeadsQuery } from "@/lib/leads-url";
import { cn } from "@/lib/cn";

interface Props {
  initial: ParsedLeadsQuery;
}

const fieldLabel =
  "mb-1.5 block text-[11px] font-medium uppercase tracking-[0.12em] text-zinc-500";

const controlClass =
  "h-10 w-full rounded-md border border-white/[0.08] bg-[#08080a] px-3 text-[13px] text-zinc-100 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] transition-[border-color,box-shadow] duration-150 ease-out hover:border-white/[0.11] focus:border-brand-blue/45 focus:outline-none focus:ring-2 focus:ring-brand-blue/15";

/**
 * URL-driven filters for tier, status, text search, email presence, and ZIMS sync.
 */
export function LeadFilters({ initial }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();

  const [tier, setTier] = useState(initial.tier || "");
  const [status, setStatus] = useState(initial.status || "");
  const [search, setSearch] = useState(initial.search || "");
  const [hasEmail, setHasEmail] = useState<boolean | undefined>(initial.has_email);
  const [zims, setZims] = useState<boolean | undefined>(initial.zims_synced);

  const skipSearchDebounce = useRef(true);

  useEffect(() => {
    setTier(initial.tier || "");
    setStatus(initial.status || "");
    setSearch(initial.search || "");
    setHasEmail(initial.has_email);
    setZims(initial.zims_synced);
    skipSearchDebounce.current = true;
  }, [initial]);

  const currentView = useMemo(
    () => (params.get("view") === "kanban" ? "kanban" : "table") as ParsedLeadsQuery["view"],
    [params]
  );

  const push = useCallback(
    (patch: Partial<ParsedLeadsQuery>) => {
      const next: ParsedLeadsQuery = {
        page: patch.page ?? 1,
        per_page: patch.per_page ?? initial.per_page,
        tier: "tier" in patch ? patch.tier || undefined : tier || undefined,
        status: "status" in patch ? patch.status || undefined : status || undefined,
        search: "search" in patch ? patch.search || undefined : search || undefined,
        has_email: "has_email" in patch ? patch.has_email : hasEmail,
        zims_synced: "zims_synced" in patch ? patch.zims_synced : zims,
        view: patch.view ?? currentView,
      };
      const qs = stringifyLeadsQuery(next);
      startTransition(() => {
        router.push(`${pathname}?${qs}`);
        router.refresh();
      });
    },
    [router, pathname, initial.per_page, tier, status, search, hasEmail, zims, currentView]
  );

  const pushRef = useRef(push);
  pushRef.current = push;

  useEffect(() => {
    if (skipSearchDebounce.current) {
      skipSearchDebounce.current = false;
      return;
    }
    const t = window.setTimeout(() => {
      pushRef.current({ search: search || undefined, page: 1 });
    }, 450);
    return () => window.clearTimeout(t);
  }, [search]);

  const hasActiveFilters = Boolean(
    initial.tier ||
      initial.status ||
      initial.search ||
      initial.has_email === true ||
      initial.zims_synced === true
  );

  function clearAll() {
    setTier("");
    setStatus("");
    setSearch("");
    setHasEmail(undefined);
    setZims(undefined);
    skipSearchDebounce.current = true;
    const next: ParsedLeadsQuery = {
      page: 1,
      per_page: initial.per_page,
      view: currentView,
    };
    startTransition(() => {
      router.push(`${pathname}?${stringifyLeadsQuery(next)}`);
      router.refresh();
    });
  }

  function chipRemove(key: keyof Pick<ParsedLeadsQuery, "tier" | "status" | "search" | "has_email" | "zims_synced">) {
    const patch: Partial<ParsedLeadsQuery> = { page: 1 };
    if (key === "tier") {
      patch.tier = undefined;
      setTier("");
    }
    if (key === "status") {
      patch.status = undefined;
      setStatus("");
    }
    if (key === "search") {
      patch.search = undefined;
      setSearch("");
      skipSearchDebounce.current = true;
    }
    if (key === "has_email") {
      patch.has_email = undefined;
      setHasEmail(undefined);
    }
    if (key === "zims_synced") {
      patch.zims_synced = undefined;
      setZims(undefined);
    }
    pushRef.current(patch);
  }

  return (
    <div className="rounded-lg border border-white/[0.06] bg-[#09090b]/60 p-5 shadow-md shadow-black/20 sm:p-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 text-zinc-400">
          <div className="flex h-7 w-7 items-center justify-center rounded-md border border-white/[0.06] bg-white/[0.03]">
            <Filter className="h-3.5 w-3.5" />
          </div>
          <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
            Filters
          </span>
        </div>
        {hasActiveFilters ? (
          <button
            type="button"
            onClick={clearAll}
            className="h-9 rounded-md border border-white/[0.08] px-3 text-[12px] font-medium text-zinc-400 transition-colors hover:border-white/[0.12] hover:bg-white/[0.04] hover:text-zinc-200"
          >
            Clear filters
          </button>
        ) : null}
      </div>

      {hasActiveFilters ? (
        <div className="mb-5 flex flex-wrap gap-2">
          {initial.tier ? (
            <Chip label={`Tier: ${initial.tier}`} onRemove={() => chipRemove("tier")} />
          ) : null}
          {initial.status ? (
            <Chip label={`Status: ${initial.status}`} onRemove={() => chipRemove("status")} />
          ) : null}
          {initial.search ? (
            <Chip
              label={`Search: “${initial.search.length > 28 ? `${initial.search.slice(0, 28)}…` : initial.search}”`}
              onRemove={() => chipRemove("search")}
            />
          ) : null}
          {initial.has_email === true ? (
            <Chip label="Has email" onRemove={() => chipRemove("has_email")} />
          ) : null}
          {initial.zims_synced === true ? (
            <Chip label="Synced to ZIMS" onRemove={() => chipRemove("zims_synced")} />
          ) : null}
        </div>
      ) : null}

      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4 lg:gap-6">
        <label className="block min-w-0">
          <span className={fieldLabel}>Tier</span>
          <select
            value={tier}
            onChange={(e) => setTier(e.target.value)}
            className={controlClass}
          >
            <option value="">All tiers</option>
            <option value="hot">Hot</option>
            <option value="warm">Warm</option>
            <option value="potential">Potential</option>
            <option value="cold">Cold</option>
          </select>
        </label>
        <label className="block min-w-0">
          <span className={fieldLabel}>Status</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className={controlClass}
          >
            <option value="">All statuses</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="replied">Replied</option>
            <option value="meeting">Meeting</option>
            <option value="closed">Closed</option>
            <option value="lost">Lost</option>
            <option value="suppressed">Suppressed</option>
          </select>
        </label>
        <label className="block min-w-0 md:col-span-2">
          <span className={fieldLabel}>Search</span>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Company, email, industry, notes…"
              className={`${controlClass} pl-10`}
            />
          </div>
          <p className="mt-1.5 text-[11px] text-zinc-600">Search updates the URL after you pause typing (~450ms).</p>
        </label>
      </div>

      <div className="mt-6 flex flex-col gap-4 border-t border-white/[0.06] pt-6 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-6">
          <label className="flex cursor-pointer items-center gap-2.5 text-[13px] text-zinc-400 transition-colors hover:text-zinc-300">
            <input
              type="checkbox"
              checked={hasEmail === true}
              onChange={() => setHasEmail((v) => (v === true ? undefined : true))}
              className="h-3.5 w-3.5 rounded border-white/[0.12] bg-[#08080a] text-brand-blue accent-brand-blue focus:ring-2 focus:ring-brand-blue/25"
            />
            Has email
          </label>
          <label className="flex cursor-pointer items-center gap-2.5 text-[13px] text-zinc-400 transition-colors hover:text-zinc-300">
            <input
              type="checkbox"
              checked={zims === true}
              onChange={() => setZims((v) => (v === true ? undefined : true))}
              className="h-3.5 w-3.5 rounded border-white/[0.12] bg-[#08080a] text-brand-blue accent-brand-blue focus:ring-2 focus:ring-brand-blue/25"
            />
            Synced to ZIMS
          </label>
        </div>
        <button
          type="button"
          disabled={pending}
          onClick={() =>
            push({
              tier: tier || undefined,
              status: status || undefined,
              search: search || undefined,
              has_email: hasEmail,
              zims_synced: zims,
              page: 1,
            })
          }
          className="h-10 shrink-0 rounded-md bg-zinc-100 px-5 text-[13px] font-medium text-zinc-900 shadow-sm transition-[background-color,transform,opacity] duration-150 ease-out hover:bg-white active:scale-[0.98] disabled:pointer-events-none disabled:opacity-40 sm:self-end"
        >
          Apply filters
        </button>
      </div>
    </div>
  );
}

function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span
      className={cn(
        "inline-flex max-w-full items-center gap-1.5 rounded-full border border-white/[0.1] bg-white/[0.04] py-1 pl-3 pr-1 text-[12px] font-medium text-zinc-300 shadow-sm"
      )}
    >
      <span className="truncate">{label}</span>
      <button
        type="button"
        aria-label={`Remove ${label}`}
        onClick={onRemove}
        className="rounded-full p-1 text-zinc-500 transition-colors hover:bg-white/[0.08] hover:text-zinc-200"
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}
