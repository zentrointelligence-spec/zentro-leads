"use client";

import {
  createColumnHelper,
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { ArrowUpDown, Flame, Zap, TrendingUp, Snowflake } from "lucide-react";

import type { Lead } from "@/lib/api";
import { emailFromLead, companyNameFromLead } from "@/lib/lead-view";
import { cn } from "@/lib/cn";

interface Props {
  leads: Lead[];
  onRowClick: (lead: Lead) => void;
}

const TIER_ICONS: Record<string, React.ElementType> = {
  hot: Flame,
  warm: Zap,
  potential: TrendingUp,
  cold: Snowflake,
};

const TIER_COLORS: Record<string, { text: string; bg: string }> = {
  hot: { text: "#ef4444", bg: "rgba(239,68,68,0.08)" },
  warm: { text: "#f59e0b", bg: "rgba(245,158,11,0.08)" },
  potential: { text: "#f59e0b", bg: "rgba(245,158,11,0.08)" },
  cold: { text: "#6b7280", bg: "rgba(107,114,128,0.08)" },
};

const STATUS_BADGES: Record<string, { label: string; color: string; bg: string }> = {
  new: { label: "New", color: "#3b82f6", bg: "rgba(59,130,246,0.08)" },
  contacted: { label: "Contacted", color: "#f59e0b", bg: "rgba(245,158,11,0.08)" },
  replied: { label: "Replied", color: "#eab308", bg: "rgba(234,179,8,0.08)" },
  meeting: { label: "Meeting", color: "#a855f7", bg: "rgba(168,85,247,0.08)" },
  closed: { label: "Closed", color: "#10b981", bg: "rgba(16,185,129,0.08)" },
  lost: { label: "Lost", color: "#6b7280", bg: "rgba(107,114,128,0.08)" },
};

const columnHelper = createColumnHelper<Lead>();

export function LeadTableView({ leads, onRowClick }: Props) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "score", desc: true }]);

  const columns = [
    columnHelper.accessor((row) => companyNameFromLead(row), {
      id: "company",
      header: "Company",
      cell: ({ row }) => {
        const name = companyNameFromLead(row.original);
        const initials = name
          ? name
            .split(/\s+/)
            .slice(0, 2)
            .map((w) => w[0]?.toUpperCase())
            .join("")
          : "?";
        return (
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg text-xs font-bold" style={{ backgroundColor: "var(--bg-tertiary)", color: "var(--text-secondary)" }}>
              {initials}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>{name}</p>
              <p className="text-[11px] truncate" style={{ color: "var(--text-tertiary)" }}>{emailFromLead(row.original) ?? "—"}</p>
            </div>
          </div>
        );
      },
    }),
    columnHelper.accessor((row) => row.lead_tier, {
      id: "tier",
      header: "Tier",
      cell: ({ getValue }) => {
        const tier = getValue() || "potential";
        const Icon = TIER_ICONS[tier] || TrendingUp;
        const meta = TIER_COLORS[tier] || TIER_COLORS.potential;
        return (
          <div className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold capitalize" style={{ backgroundColor: meta.bg, color: meta.text }}>
            <Icon className="h-3 w-3" />
            {tier}
          </div>
        );
      },
    }),
    columnHelper.accessor((row) => row.lead_score, {
      id: "score",
      header: "Score",
      cell: ({ getValue }) => {
        const score = getValue() ?? 0;
        return (
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-16 rounded-full overflow-hidden" style={{ backgroundColor: "var(--bg-tertiary)" }}>
              <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(100, score)}%`, backgroundColor: score >= 80 ? "#10b981" : score >= 50 ? "#f59e0b" : "#ef4444" }} />
            </div>
            <span className="text-xs font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{score}</span>
          </div>
        );
      },
    }),
    columnHelper.accessor((row) => row.icp_match_score, {
      id: "icp_match",
      header: "ICP Match",
      cell: ({ getValue }) => {
        const val = getValue() ?? 0;
        return (
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-16 rounded-full overflow-hidden" style={{ backgroundColor: "var(--bg-tertiary)" }}>
              <div className="h-full rounded-full transition-all" style={{ width: `${val}%`, backgroundColor: val >= 70 ? "#10b981" : val >= 40 ? "#f59e0b" : "#ef4444" }} />
            </div>
            <span className="text-xs font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{val}%</span>
          </div>
        );
      },
    }),
    columnHelper.accessor((row) => row.status, {
      id: "status",
      header: "Status",
      cell: ({ getValue }) => {
        const status = getValue() || "new";
        const meta = STATUS_BADGES[status] || STATUS_BADGES.new;
        return (
          <span className="inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold" style={{ backgroundColor: meta.bg, color: meta.color }}>
            {meta.label}
          </span>
        );
      },
    }),
    columnHelper.accessor((row) => row.person?.phone ?? null, {
      id: "contact",
      header: "Contact",
      cell: ({ row }) => {
        const phone = row.original.person?.phone;
        const email = emailFromLead(row.original);
        return (
          <div className="flex flex-col gap-0.5">
            {phone ? <span className="text-xs" style={{ color: "var(--text-secondary)" }}>{phone}</span> : null}
            {email ? <span className="text-[11px] truncate" style={{ color: "var(--text-tertiary)" }}>{email}</span> : <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>—</span>}
          </div>
        );
      },
    }),
    columnHelper.display({
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <button
          className="rounded-md px-2.5 py-1.5 text-[11px] font-medium opacity-0 group-hover:opacity-100 transition-opacity"
          style={{ backgroundColor: "var(--color-brand-bg)", color: "var(--color-brand)" }}
          onClick={(e) => { e.stopPropagation(); onRowClick(row.original); }}
        >
          View
        </button>
      ),
    }),
  ];

  const table = useReactTable({
    data: leads,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: { sorting },
  });

  return (
    <div className="overflow-x-auto rounded-xl" style={{ border: "1px solid var(--border-primary)" }}>
      <table className="w-full text-left">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} style={{ borderBottom: "1px solid var(--border-primary)" }}>
              {hg.headers.map((h) => (
                <th key={h.id} className="px-4 py-3 text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>
                  {h.isPlaceholder ? null : (
                    <button
                      className={cn("flex items-center gap-1 transition-colors hover:text-primary", h.column.getCanSort() ? "cursor-pointer select-none" : "")}
                      onClick={h.column.getToggleSortingHandler()}
                    >
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      {h.column.getCanSort() && <ArrowUpDown className="h-3 w-3" />}
                    </button>
                  )}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className="group cursor-pointer transition-colors hover:bg-hover"
              onClick={() => onRowClick(row.original)}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-4 py-3" style={{ borderBottom: "1px solid var(--border-primary)" }}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
