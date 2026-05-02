"use client";

import { useState, useMemo, useCallback } from "react";
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
  useDraggable,
  useDroppable,
  type DragEndEvent,
  type DragStartEvent,
  type DragOverEvent,
} from "@dnd-kit/core";
import {
  Flame, Zap, TrendingUp, Snowflake, Mail, Eye, Phone,
  MessageCircle, User
} from "lucide-react";
import { toast } from "sonner";

import type { Lead, LeadStatus } from "@/lib/api";
import { emailFromLead, companyNameFromLead } from "@/lib/lead-view";
import { patchLeadStatus } from "@/lib/leads-client";
import { useIsClient } from "@/lib/use-is-client";
import { cn } from "@/lib/cn";

const STATUS_MAP: Record<string, LeadStatus> = {
  NEW: "new",
  CONTACTED: "contacted",
  REPLIED: "replied",
  MEETING: "meeting",
  CLOSED: "closed",
  LOST: "lost",
};

const COLUMNS: { id: LeadStatus; label: string; color: string; bg: string }[] = [
  { id: "new", label: "New", color: "#3b82f6", bg: "rgba(59,130,246,0.06)" },
  { id: "contacted", label: "Contacted", color: "#f59e0b", bg: "rgba(245,158,11,0.06)" },
  { id: "replied", label: "Replied", color: "#eab308", bg: "rgba(234,179,8,0.06)" },
  { id: "meeting", label: "Meeting", color: "#a855f7", bg: "rgba(168,85,247,0.06)" },
  { id: "closed", label: "Closed", color: "#10b981", bg: "rgba(16,185,129,0.06)" },
  { id: "lost", label: "Lost", color: "#6b7280", bg: "rgba(107,114,128,0.06)" },
];

const TIER_META: Record<string, { icon: React.ElementType; color: string }> = {
  hot: { icon: Flame, color: "#ef4444" },
  warm: { icon: Zap, color: "#f59e0b" },
  potential: { icon: TrendingUp, color: "#f59e0b" },
  cold: { icon: Snowflake, color: "#6b7280" },
};

/* ── Presentational card UI (no DnD hooks) ── */
function LeadCardContent({
  lead,
  onClick,
  onContact,
  dragStyle,
  isDragging,
  dragProps,
}: {
  lead: Lead;
  onClick: () => void;
  onContact: (e: React.MouseEvent) => void;
  dragStyle?: React.CSSProperties;
  isDragging?: boolean;
  dragProps?: {
    ref: React.Ref<HTMLDivElement>;
    listeners?: object;
    attributes?: object;
  };
}) {
  const name = companyNameFromLead(lead);
  const email = emailFromLead(lead);
  const phone = lead.person?.phone ?? lead.company?.phone ?? null;
  const score = lead.lead_score ?? 0;
  const tier = lead.lead_tier || "potential";
  const tierMeta = TIER_META[tier] || TIER_META.potential;
  const TierIcon = tierMeta.icon;

  const signals = lead.intent_signals ?? [];
  const icpMatch = lead.icp_match_score ?? 0;
  const initials = name
    ? name
      .split(/\s+/)
      .slice(0, 2)
      .map((w) => w[0]?.toUpperCase())
      .join("")
    : "?";

  const industry = lead.company?.industry;
  const size = lead.company?.employee_range;
  const contactName = lead.person?.full_name;
  const contactTitle = lead.person?.job_title;
  const emailConfidence = lead.person?.email_confidence;

  return (
    <div
      ref={dragProps?.ref}
      {...(dragProps?.listeners ?? {})}
      {...(dragProps?.attributes ?? {})}
      className={cn(
        "group cursor-grab rounded-xl p-3.5 transition-all hover:shadow-md",
        isDragging && "opacity-50 scale-95 shadow-lg"
      )}
      style={{
        ...(dragStyle ?? {}),
        backgroundColor: "var(--bg-card)",
        border: "1px solid var(--border-primary)",
      }}
      onClick={onClick}
    >
      {/* Top: Avatar + name + score */}
      <div className="flex items-start gap-2.5">
        <div
          className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg text-xs font-bold"
          style={{ backgroundColor: "var(--bg-tertiary)", color: "var(--text-secondary)" }}
        >
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
            {name}
          </p>
          {(industry || size) && (
            <p className="text-[11px] truncate mt-0.5" style={{ color: "var(--text-tertiary)" }}>
              {industry}{industry && size ? " · " : ""}{size}
            </p>
          )}
        </div>
        <div
          className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-extrabold"
          style={{ backgroundColor: "var(--bg-tertiary)", color: "var(--text-primary)" }}
        >
          {score}
        </div>
      </div>

      {/* Tier + Contact */}
      <div className="mt-2 flex items-center gap-2 flex-wrap">
        <div className="flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold" style={{ backgroundColor: tierMeta.color + "15", color: tierMeta.color }}>
          <TierIcon className="h-3 w-3" />
          {tier}
        </div>
        {contactName && (
          <div className="flex items-center gap-1 text-[10px]" style={{ color: "var(--text-tertiary)" }}>
            <User className="h-3 w-3" />
            {contactName}{contactTitle ? ` — ${contactTitle}` : ""}
          </div>
        )}
      </div>

      {/* Phone */}
      {phone && (
        <div className="mt-1.5 flex items-center gap-1.5 text-[11px]" style={{ color: "var(--text-secondary)" }}>
          <Phone className="h-3 w-3" style={{ color: "var(--text-tertiary)" }} />
          {phone}
        </div>
      )}

      {/* Email with confidence */}
      {email && (
        <div className="mt-1 flex items-center gap-1.5 text-[11px]" style={{ color: "var(--text-secondary)" }}>
          <Mail className="h-3 w-3" style={{ color: "var(--text-tertiary)" }} />
          <span className="truncate">{email}</span>
          {emailConfidence ? (
            <span className="text-[10px] font-medium" style={{ color: emailConfidence >= 80 ? "#10b981" : emailConfidence >= 50 ? "#f59e0b" : "#ef4444" }}>
              {emailConfidence}%
            </span>
          ) : null}
        </div>
      )}

      {/* ICP Match */}
      <div className="mt-2.5 flex items-center gap-2">
        <span className="text-[10px] font-medium" style={{ color: "var(--text-tertiary)" }}>ICP</span>
        <div className="h-1.5 flex-1 rounded-full overflow-hidden" style={{ backgroundColor: "var(--bg-tertiary)" }}>
          <div
            className="h-full rounded-full"
            style={{
              width: `${icpMatch}%`,
              backgroundColor: icpMatch >= 70 ? "#10b981" : icpMatch >= 40 ? "#f59e0b" : "#ef4444",
            }}
          />
        </div>
        <span className="text-[10px] font-bold tabular-nums" style={{ color: icpMatch >= 70 ? "#10b981" : "var(--text-tertiary)" }}>
          {icpMatch}%{icpMatch >= 70 ? " ✅" : ""}
        </span>
      </div>

      {/* Signals */}
      {signals.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {signals.slice(0, 3).map((s: string, idx: number) => (
            <span
              key={`${lead.id}-sig-${idx}`}
              className="inline-block rounded px-1.5 py-0.5 text-[10px] font-medium"
              style={{ backgroundColor: "var(--color-brand-bg)", color: "var(--color-brand)" }}
            >
              {s}
            </span>
          ))}
        </div>
      )}

      {/* Action buttons */}
      <div className="mt-3 flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          className="flex h-7 items-center gap-1 rounded-md px-2 text-[10px] font-medium transition-colors"
          style={{ backgroundColor: "var(--bg-tertiary)", color: "var(--text-tertiary)" }}
          title="View lead"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => { e.stopPropagation(); onClick(); }}
        >
          <Eye className="h-3 w-3" /> View
        </button>
        {email && (
          <button
            className="flex h-7 items-center gap-1 rounded-md px-2 text-[10px] font-medium transition-colors"
            style={{ backgroundColor: "var(--bg-tertiary)", color: "var(--text-tertiary)" }}
            title="Email"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={onContact}
          >
            <Mail className="h-3 w-3" />
          </button>
        )}
        {phone && (
          <button
            className="flex h-7 items-center gap-1 rounded-md px-2 text-[10px] font-medium transition-colors"
            style={{ backgroundColor: "var(--bg-tertiary)", color: "var(--text-tertiary)" }}
            title="WhatsApp"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation();
              const clean = phone!.replace(/\D/g, "");
              window.open(`https://wa.me/${clean}`, "_blank", "noopener,noreferrer");
            }}
          >
            <MessageCircle className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  );
}

/* ── Static card (SSR / no DnD) ── */
function StaticLeadCard({
  lead,
  onClick,
  onContact,
}: {
  lead: Lead;
  onClick: () => void;
  onContact: (e: React.MouseEvent) => void;
}) {
  return <LeadCardContent lead={lead} onClick={onClick} onContact={onContact} />;
}

/* ── Draggable card (client only) ── */
function DraggableLeadCard({
  lead,
  onClick,
  onContact,
}: {
  lead: Lead;
  onClick: () => void;
  onContact: (e: React.MouseEvent) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: lead.id,
    data: { status: lead.status, lead },
  });

  const dragStyle = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;

  return (
    <LeadCardContent
      lead={lead}
      onClick={onClick}
      onContact={onContact}
      dragStyle={dragStyle}
      isDragging={isDragging}
      dragProps={{ ref: setNodeRef, listeners, attributes }}
    />
  );
}

/* ── Droppable column ── */
function KanbanColumn({
  col,
  count,
  isOver,
  children,
}: {
  col: (typeof COLUMNS)[number];
  count: number;
  isOver: boolean;
  children: React.ReactNode;
}) {
  const { setNodeRef } = useDroppable({ id: col.id });

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex w-72 flex-shrink-0 flex-col rounded-xl p-3 transition-all",
        isOver && "ring-2 ring-[var(--color-brand)]"
      )}
      style={{
        backgroundColor: isOver ? "var(--color-brand-bg)" : col.bg,
      }}
    >
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full" style={{ backgroundColor: col.color }} />
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
            {col.label}
          </span>
        </div>
        <span
          className="text-[11px] font-bold tabular-nums rounded-md px-1.5 py-0.5"
          style={{ backgroundColor: "var(--bg-tertiary)", color: "var(--text-tertiary)" }}
        >
          {count}
        </span>
      </div>
      <div className="flex flex-col gap-2.5 min-h-[80px]">{children}</div>
    </div>
  );
}

/* ── Static column (SSR) ── */
function StaticColumn({
  col,
  count,
  children,
}: {
  col: (typeof COLUMNS)[number];
  count: number;
  children: React.ReactNode;
}) {
  return (
    <div
      className="flex w-72 flex-shrink-0 flex-col rounded-xl p-3"
      style={{ backgroundColor: col.bg }}
    >
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full" style={{ backgroundColor: col.color }} />
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
            {col.label}
          </span>
        </div>
        <span
          className="text-[11px] font-bold tabular-nums rounded-md px-1.5 py-0.5"
          style={{ backgroundColor: "var(--bg-tertiary)", color: "var(--text-tertiary)" }}
        >
          {count}
        </span>
      </div>
      <div className="flex flex-col gap-2.5 min-h-[80px]">{children}</div>
    </div>
  );
}

export function LeadKanban({
  leads,
  onLeadUpdated,
  onView,
  onQuickContact,
  onDragError,
}: {
  leads: Lead[];
  onLeadUpdated: (l: Lead) => void;
  onView: (l: Lead) => void;
  onQuickContact: (l: Lead) => void;
  onDragError: (m: string) => void;
}) {
  const isClient = useIsClient();
  const [activeDragId, setActiveDragId] = useState<string | null>(null);
  const [overColumnId, setOverColumnId] = useState<string | null>(null);

  const byColumn = useMemo(() => {
    const m = new Map<LeadStatus, Lead[]>();
    COLUMNS.forEach((c) => m.set(c.id, []));
    leads.forEach((l) => {
      const key = l.status ?? "new";
      if (!m.has(key as LeadStatus)) m.set(key as LeadStatus, []);
      m.get(key as LeadStatus)!.push(l);
    });
    return m;
  }, [leads]);

  const activeLead = useMemo(
    () => (activeDragId ? leads.find((l) => l.id === activeDragId) ?? null : null),
    [activeDragId, leads]
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const handleDragStart = useCallback(({ active }: DragStartEvent) => {
    setActiveDragId(active.id as string);
  }, []);

  const handleDragOver = useCallback(({ over }: DragOverEvent) => {
    setOverColumnId(over ? (over.id as string) : null);
  }, []);

  const handleDragEnd = useCallback(
    ({ active, over }: DragEndEvent) => {
      setActiveDragId(null);
      setOverColumnId(null);

      if (!over) return;

      const leadId = active.id as string;
      const fromStatus = active.data.current?.status as LeadStatus;
      const rawTarget = over.id as string;
      const toStatus = STATUS_MAP[rawTarget.toUpperCase()] ?? (rawTarget as LeadStatus);

      if (!toStatus || fromStatus === toStatus) return;

      const lead = leads.find((l) => l.id === leadId);
      if (!lead) return;

      // Optimistic update
      const optimisticLead = { ...lead, status: toStatus };
      onLeadUpdated(optimisticLead);
      toast.success(`Lead moved to ${COLUMNS.find((c) => c.id === toStatus)?.label ?? toStatus}`);

      // API call
      patchLeadStatus(leadId, toStatus)
        .then((updated) => {
          onLeadUpdated(updated);
        })
        .catch(() => {
          // Revert on error
          onLeadUpdated(lead);
          onDragError(`Could not move lead to ${toStatus}`);
        });
    },
    [leads, onLeadUpdated, onDragError]
  );

  // SSR: render static non-draggable kanban (prevents hydration mismatch)
  if (!isClient) {
    return (
      <div className="overflow-x-auto pb-2">
        <div className="flex gap-4 min-w-max">
          {COLUMNS.map((col) => {
            const items = byColumn.get(col.id) ?? [];
            return (
              <StaticColumn key={col.id} col={col} count={items.length}>
                {items.map((lead) => (
                  <StaticLeadCard
                    key={lead.id}
                    lead={lead}
                    onClick={() => onView(lead)}
                    onContact={(e) => {
                      e.stopPropagation();
                      onQuickContact(lead);
                    }}
                  />
                ))}
                {items.length === 0 && (
                  <div
                    className="rounded-lg border border-dashed py-8 text-center"
                    style={{ borderColor: "var(--border-primary)" }}
                  >
                    <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>Drop leads here</p>
                  </div>
                )}
              </StaticColumn>
            );
          })}
        </div>
      </div>
    );
  }

  // Client: full DnD kanban
  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="overflow-x-auto pb-2">
        <div className="flex gap-4 min-w-max">
          {COLUMNS.map((col) => {
            const items = byColumn.get(col.id) ?? [];
            const isOver = overColumnId === col.id && activeDragId !== null;
            return (
              <KanbanColumn key={col.id} col={col} count={items.length} isOver={isOver}>
                {items.map((lead) => (
                  <DraggableLeadCard
                    key={lead.id}
                    lead={lead}
                    onClick={() => onView(lead)}
                    onContact={(e) => {
                      e.stopPropagation();
                      onQuickContact(lead);
                    }}
                  />
                ))}
                {items.length === 0 && !isOver && (
                  <div
                    className="rounded-lg border border-dashed py-8 text-center"
                    style={{ borderColor: "var(--border-primary)" }}
                  >
                    <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>Drop leads here</p>
                  </div>
                )}
              </KanbanColumn>
            );
          })}
        </div>
      </div>

      <DragOverlay>
        {activeLead ? (
          <div
            className="rounded-xl p-3.5 shadow-lg rotate-2 scale-105"
            style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--color-brand)" }}
          >
            <div className="flex items-start gap-2.5">
              <div
                className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg text-xs font-bold"
                style={{ backgroundColor: "var(--bg-tertiary)", color: "var(--text-primary)" }}
              >
                {companyNameFromLead(activeLead).slice(0, 2).toUpperCase()}
              </div>
              <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                {companyNameFromLead(activeLead)}
              </p>
            </div>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
