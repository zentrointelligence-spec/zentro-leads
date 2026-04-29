"use client";

import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { Mail, MousePointerClick } from "lucide-react";

import type { Lead } from "@/lib/api";
import { companyNameFromLead } from "@/lib/lead-view";
import { cn } from "@/lib/cn";

function priorityLabel(tier: string): { label: string; className: string } {
  switch (tier) {
    case "hot":
      return {
        label: "Critical",
        className:
          "border-rose-500/35 bg-gradient-to-r from-rose-500/15 to-orange-500/10 text-rose-600 dark:text-rose-300",
      };
    case "warm":
      return {
        label: "High",
        className:
          "border-amber-500/35 bg-gradient-to-r from-amber-500/15 to-yellow-500/10 text-amber-700 dark:text-amber-300",
      };
    case "potential":
      return {
        label: "Medium",
        className:
          "border-sky-500/35 bg-gradient-to-r from-sky-500/15 to-indigo-500/10 text-sky-700 dark:text-sky-300",
      };
    default:
      return {
        label: "Standard",
        className: "border-[color:var(--border-color)] bg-[color:var(--accent-soft)] text-[color:var(--text-secondary)]",
      };
  }
}

function ScoreRing({ score, id }: { score: number; id: string }) {
  const pct = Math.min(100, Math.max(0, score));
  const r = 20;
  const c = 2 * Math.PI * r;
  const dash = c - (pct / 100) * c;

  return (
    <div className="relative h-14 w-14 flex-shrink-0">
      <svg className="-rotate-90" width="56" height="56" viewBox="0 0 56 56">
        <circle
          cx="28"
          cy="28"
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          className="text-[color:var(--border-color)]"
        />
        <circle
          cx="28"
          cy="28"
          r={r}
          fill="none"
          stroke={`url(#scoreGrad-${id})`}
          strokeWidth="4"
          strokeDasharray={c}
          strokeDashoffset={dash}
          strokeLinecap="round"
          className="transition-all duration-700 ease-out"
        />
        <defs>
          <linearGradient id={`scoreGrad-${id}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#a855f7" />
          </linearGradient>
        </defs>
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[11px] font-bold tabular-nums text-[color:var(--text-primary)]">
        {score}
      </span>
    </div>
  );
}

interface Props {
  lead: Lead;
  onView: (lead: Lead) => void;
  onQuickContact: (lead: Lead) => void;
}

/**
 * Glass pipeline card with score ring, priority, and hover actions.
 */
export function LeadCard({ lead, onView, onQuickContact }: Props) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: lead.id,
    data: { lead },
  });

  const style = transform
    ? {
        transform: CSS.Translate.toString(transform),
        zIndex: isDragging ? 50 : undefined,
        opacity: isDragging ? 0.35 : undefined,
      }
    : undefined;

  const company = companyNameFromLead(lead);
  const pr = priorityLabel(lead.lead_tier);

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={cn(
        "group relative rounded-2xl border border-[color:var(--border-color)]",
        "bg-[color:var(--card-bg)] backdrop-blur-xl shadow-[var(--shadow-sm)]",
        "transition-all duration-300 ease-out",
        "hover:-translate-y-0.5 hover:scale-[1.02] hover:shadow-[var(--shadow-glow)]",
        isDragging && "scale-105 opacity-90 ring-2 ring-[color:var(--accent)] shadow-[var(--shadow-glow)]"
      )}
    >
      <div className="flex gap-3 p-4">
        <ScoreRing score={lead.lead_score} id={lead.id} />
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-sm text-[color:var(--text-primary)] truncate">{company}</p>
          <span
            className={cn(
              "mt-1 inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
              pr.className
            )}
          >
            {pr.label}
          </span>
        </div>
      </div>

      <div
        className={cn(
          "flex gap-2 border-t border-[color:var(--border-color)] px-3 py-2",
          "opacity-0 translate-y-1 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-200"
        )}
      >
        <button
          type="button"
          className={cn(
            "inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg py-1.5 text-xs font-medium",
            "text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)]",
            "hover:bg-[color:var(--accent-soft)] btn-ripple"
          )}
          onClick={(e) => {
            e.stopPropagation();
            onView(lead);
          }}
        >
          <MousePointerClick className="h-3.5 w-3.5" />
          View
        </button>
        <button
          type="button"
          className={cn(
            "inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg py-1.5 text-xs font-medium",
            "text-[color:var(--accent)] hover:bg-[color:var(--accent-soft)] btn-ripple"
          )}
          onClick={(e) => {
            e.stopPropagation();
            onQuickContact(lead);
          }}
        >
          <Mail className="h-3.5 w-3.5" />
          Quick contact
        </button>
      </div>
    </div>
  );
}
