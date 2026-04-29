"use client";

import { memo, useMemo, useState, useTransition } from "react";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { Ban, CloudUpload, Eye, Loader2 } from "lucide-react";

import type { Lead } from "@/lib/api";
import {
  companyNameFromLead,
  emailFromLead,
  industryFromLead,
  tierBadgeClass,
} from "@/lib/lead-view";
import { cn } from "@/lib/cn";

import { useLeadsDashboardActions } from "./leads-dashboard-context";

interface PaginatedMeta {
  page: number;
  pages: number;
  total: number;
  per_page: number;
}

interface Props {
  leads: Lead[];
  paginated: PaginatedMeta;
  manualFromNl: boolean;
  onPageChange: (page: number) => void;
  onView: (lead: Lead) => void;
  isNavigating?: boolean;
}

function LeadRowActions({
  lead,
  onView,
}: {
  lead: Lead;
  onView: (lead: Lead) => void;
}) {
  const { suppressLeadOptimistic, syncZimsOptimistic } = useLeadsDashboardActions();
  const [busy, setBusy] = useState(false);

  return (
    <div className="flex flex-wrap items-center justify-end gap-1.5">
      <button
        type="button"
        onClick={() => onView(lead)}
        className="inline-flex h-8 items-center gap-1.5 rounded-md border border-white/[0.08] px-2.5 text-[12px] font-medium text-zinc-300 shadow-sm transition-[border-color,background-color,transform] duration-150 hover:border-white/[0.12] hover:bg-white/[0.04] hover:text-zinc-100 active:scale-[0.97]"
      >
        <Eye className="h-3.5 w-3.5 opacity-70" />
        View
      </button>
      <button
        type="button"
        disabled={busy}
        onClick={() => {
          void (async () => {
            setBusy(true);
            try {
              await suppressLeadOptimistic(lead);
            } finally {
              setBusy(false);
            }
          })();
        }}
        className="inline-flex h-8 items-center gap-1.5 rounded-md border border-red-500/20 px-2.5 text-[12px] font-medium text-red-300/95 transition-[border-color,background-color,transform] duration-150 hover:border-red-500/35 hover:bg-red-500/[0.08] active:scale-[0.97] disabled:pointer-events-none disabled:opacity-40"
      >
        {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Ban className="h-3.5 w-3.5 opacity-80" />}
        Suppress
      </button>
      <button
        type="button"
        disabled={busy}
        onClick={() => {
          void (async () => {
            setBusy(true);
            try {
              await syncZimsOptimistic(lead);
            } finally {
              setBusy(false);
            }
          })();
        }}
        className="inline-flex h-8 items-center gap-1.5 rounded-md bg-brand-blue px-2.5 text-[12px] font-medium text-white shadow-md transition-[background-color,transform,opacity] duration-150 ease-out hover:bg-brand-blue-dark active:scale-[0.97] disabled:pointer-events-none disabled:opacity-40"
      >
        {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CloudUpload className="h-3.5 w-3.5 opacity-90" />}
        ZIMS
      </button>
    </div>
  );
}

function TableSkeletonRows() {
  return (
    <>
      {Array.from({ length: 6 }).map((_, i) => (
        <tr key={i} className="border-b border-white/[0.04]">
          <td colSpan={7} className="px-5 py-3">
            <div className="h-4 w-full animate-pulse rounded-md bg-white/[0.06]" />
          </td>
        </tr>
      ))}
    </>
  );
}

const MobileLeadRow = memo(function MobileLeadRow({
  lead,
  onView,
}: {
  lead: Lead;
  onView: (lead: Lead) => void;
}) {
  return (
    <div className="rounded-lg border border-white/[0.06] bg-[#08080a]/80 p-4 shadow-sm transition-[box-shadow,transform] duration-200 hover:shadow-md hover:-translate-y-px">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[13px] font-medium tracking-tight text-zinc-100">
            {companyNameFromLead(lead)}
          </p>
          <p className="mt-0.5 text-[12px] text-zinc-500">{industryFromLead(lead) || "—"}</p>
        </div>
        <span className={tierBadgeClass(lead.lead_tier)}>{lead.lead_tier}</span>
      </div>
      <p className="mt-2 break-all text-[12px] text-zinc-400">{emailFromLead(lead) || "—"}</p>
      <div className="mt-3 flex items-center justify-between text-[12px] text-zinc-500">
        <span className="tabular-nums text-zinc-300">Score {lead.lead_score}</span>
        <span className="capitalize text-zinc-400">{lead.status}</span>
      </div>
      <div className="mt-3 border-t border-white/[0.06] pt-3">
        <LeadRowActions lead={lead} onView={onView} />
      </div>
    </div>
  );
});

/**
 * TanStack Table view with server pagination (or AI result set without paging).
 */
export function LeadTable({
  leads,
  paginated,
  manualFromNl,
  onPageChange,
  onView,
  isNavigating,
}: Props) {
  const [pending, startTransition] = useTransition();

  const columns = useMemo<ColumnDef<Lead>[]>(
    () => [
      {
        accessorKey: "company",
        header: "Company",
        cell: ({ row }) => (
          <span className="text-[13px] font-medium tracking-tight text-zinc-100">
            {companyNameFromLead(row.original)}
          </span>
        ),
      },
      {
        accessorKey: "industry",
        header: "Industry",
        cell: ({ row }) => (
          <span className="text-[13px] text-zinc-500">{industryFromLead(row.original) || "—"}</span>
        ),
      },
      {
        accessorKey: "email",
        header: "Email",
        cell: ({ row }) => (
          <span className="break-all text-[13px] text-zinc-400">{emailFromLead(row.original) || "—"}</span>
        ),
      },
      {
        accessorKey: "lead_score",
        header: "Score",
        cell: ({ row }) => (
          <span className="text-[13px] font-semibold tabular-nums tracking-tight text-zinc-200">
            {row.original.lead_score}
          </span>
        ),
      },
      {
        accessorKey: "lead_tier",
        header: "Tier",
        cell: ({ row }) => (
          <span className={tierBadgeClass(row.original.lead_tier)}>{row.original.lead_tier}</span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <span className="text-[13px] capitalize text-zinc-400">{row.original.status}</span>
        ),
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => <LeadRowActions lead={row.original} onView={onView} />,
      },
    ],
    [onView]
  );

  const table = useReactTable({
    data: leads,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    pageCount: Math.max(1, paginated.pages),
    state: {
      pagination: {
        pageIndex: Math.max(0, paginated.page - 1),
        pageSize: paginated.per_page,
      },
    },
  });

  return (
    <div className="animate-leads-fade-in space-y-3 md:space-y-0">
      <div className="space-y-3 md:hidden">
        {isNavigating
          ? Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="h-28 animate-pulse rounded-lg border border-white/[0.06] bg-[#09090b]/50 p-4 shadow-sm"
              />
            ))
          : leads.map((lead) => <MobileLeadRow key={lead.id} lead={lead} onView={onView} />)}
      </div>

      <div className="relative hidden overflow-hidden rounded-lg border border-white/[0.06] bg-[#09090b]/60 shadow-md shadow-black/25 md:block">
        <div
          className={cn(
            "overflow-x-auto transition-opacity duration-200",
            isNavigating && "pointer-events-none opacity-45"
          )}
        >
          <table className="w-full">
            <thead>
              {table.getHeaderGroups().map((hg) => (
                <tr
                  key={hg.id}
                  className="border-b border-white/[0.06] text-left text-[11px] font-medium uppercase tracking-[0.12em] text-zinc-500"
                >
                  {hg.headers.map((h) => (
                    <th key={h.id} className="whitespace-nowrap px-4 py-3 first:pl-5 last:pr-5">
                      {h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {isNavigating ? (
                <TableSkeletonRows />
              ) : (
                table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b border-white/[0.04] transition-colors duration-150 ease-out last:border-0 hover:bg-white/[0.035]"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="align-middle px-4 py-3 first:pl-5 last:pr-5">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {!manualFromNl && paginated.pages > 1 ? (
          <div className="flex flex-col gap-3 border-t border-white/[0.06] bg-[#08080a]/80 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
            <p className="text-[12px] tabular-nums text-zinc-500">
              <span className="text-zinc-400">{paginated.total}</span> leads ·{" "}
              <span className="text-zinc-400">{paginated.per_page}</span> per page
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={paginated.page <= 1 || pending}
                onClick={() =>
                  startTransition(() => {
                    onPageChange(paginated.page - 1);
                  })
                }
                className="h-8 rounded-md border border-white/[0.08] px-3 text-[12px] font-medium text-zinc-300 shadow-sm transition-[border-color,background-color,transform] duration-150 hover:border-white/[0.12] hover:bg-white/[0.04] active:scale-[0.97] disabled:pointer-events-none disabled:opacity-35"
              >
                Previous
              </button>
              <span className="min-w-[4.5rem] text-center text-[12px] tabular-nums text-zinc-500">
                {paginated.page} / {paginated.pages}
              </span>
              <button
                type="button"
                disabled={paginated.page >= paginated.pages || pending}
                onClick={() =>
                  startTransition(() => {
                    onPageChange(paginated.page + 1);
                  })
                }
                className="h-8 rounded-md border border-white/[0.08] px-3 text-[12px] font-medium text-zinc-300 shadow-sm transition-[border-color,background-color,transform] duration-150 hover:border-white/[0.12] hover:bg-white/[0.04] active:scale-[0.97] disabled:pointer-events-none disabled:opacity-35"
              >
                Next
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
