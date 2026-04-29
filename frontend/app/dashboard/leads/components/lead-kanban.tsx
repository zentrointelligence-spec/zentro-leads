"use client";

import { useMemo, useState } from "react";
import {
  closestCorners,
  DndContext,
  DragOverlay,
  PointerSensor,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";

import type { Lead, LeadStatus } from "@/lib/api";
import { patchLeadStatus } from "@/lib/leads-client";
import { companyNameFromLead } from "@/lib/lead-view";
import { cn } from "@/lib/cn";

import { LeadCard } from "./lead-card";

const PIPELINE: { status: LeadStatus; title: string }[] = [
  { status: "new", title: "New" },
  { status: "contacted", title: "Contacted" },
  { status: "replied", title: "Replied" },
  { status: "meeting", title: "Meeting" },
  { status: "closed", title: "Closed" },
  { status: "lost", title: "Lost" },
];

function KanbanColumn({
  id,
  title,
  count,
  children,
}: {
  id: LeadStatus;
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <div className="flex w-[280px] flex-shrink-0 flex-col rounded-2xl border border-[color:var(--border-color)] bg-[color:var(--card-bg)]/70 backdrop-blur-xl">
      <div
        className={cn(
          "sticky top-0 z-10 flex items-center justify-between rounded-t-2xl border-b border-[color:var(--border-color)]",
          "bg-[color:var(--header-bg)] px-3 py-2.5 backdrop-blur-xl"
        )}
      >
        <span className="text-sm font-semibold text-[color:var(--text-primary)]">{title}</span>
        <span
          className={cn(
            "tabular-nums rounded-full px-2 py-0.5 text-xs font-bold",
            "bg-[color:var(--accent-soft)] text-[color:var(--accent)]",
            "shadow-[0_0_12px_rgba(99,102,241,0.25)]"
          )}
        >
          {count}
        </span>
      </div>
      <div
        ref={setNodeRef}
        className={cn(
          "flex min-h-[200px] flex-1 flex-col gap-3 p-3 transition-all duration-200",
          isOver && "kanban-drop-active rounded-b-2xl"
        )}
      >
        {children}
      </div>
    </div>
  );
}

interface Props {
  leads: Lead[];
  onLeadUpdated: (lead: Lead) => void;
  onView: (lead: Lead) => void;
  onQuickContact: (lead: Lead) => void;
  onDragError: (message: string) => void;
}

/**
 * Primary pipeline view — glass columns, draggable cards, neon drop highlight.
 */
export function LeadKanban({ leads, onLeadUpdated, onView, onQuickContact, onDragError }: Props) {
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const grouped = useMemo(() => {
    const map: Record<string, Lead[]> = {};
    for (const col of PIPELINE) {
      map[col.status] = [];
    }
    for (const lead of leads) {
      if (lead.status === "suppressed") continue;
      const bucket = map[lead.status];
      if (bucket) bucket.push(lead);
    }
    return map;
  }, [leads]);

  const activeLead = activeId ? leads.find((l) => l.id === activeId) : null;

  function handleDragStart(e: DragStartEvent) {
    setActiveId(String(e.active.id));
  }

  function resolveTargetStatus(overId: string | undefined): LeadStatus | undefined {
    if (!overId) return undefined;
    if (PIPELINE.some((p) => p.status === overId)) {
      return overId as LeadStatus;
    }
    const hitLead = leads.find((l) => l.id === overId);
    if (hitLead && hitLead.status !== "suppressed") {
      return hitLead.status as LeadStatus;
    }
    return undefined;
  }

  async function handleDragEnd(e: DragEndEvent) {
    const { active, over } = e;
    setActiveId(null);
    if (!over) return;
    const leadId = String(active.id);
    const nextStatus = resolveTargetStatus(String(over.id));
    const lead = leads.find((l) => l.id === leadId);
    if (!lead || !nextStatus || lead.status === nextStatus) return;

    try {
      const updated = await patchLeadStatus(leadId, nextStatus);
      onLeadUpdated(updated);
    } catch (err) {
      onDragError(err instanceof Error ? err.message : "Could not move lead");
    }
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="-mx-1 flex gap-4 overflow-x-auto pb-4 pt-1 scrollbar-thin">
        {PIPELINE.map((col) => (
          <KanbanColumn key={col.status} id={col.status} title={col.title} count={grouped[col.status]?.length ?? 0}>
            {grouped[col.status]?.map((lead) => (
              <LeadCard key={lead.id} lead={lead} onView={onView} onQuickContact={onQuickContact} />
            ))}
          </KanbanColumn>
        ))}
      </div>
      <DragOverlay dropAnimation={{ duration: 220, easing: "cubic-bezier(0.34,1.56,0.64,1)" }}>
        {activeLead ? (
          <div
            className={cn(
              "w-[260px] rounded-2xl border border-[color:var(--border-color)]",
              "bg-[color:var(--card-bg)] p-4 shadow-[var(--shadow-glow)] backdrop-blur-xl"
            )}
          >
            <p className="text-sm font-semibold text-[color:var(--text-primary)]">
              {companyNameFromLead(activeLead)}
            </p>
            <p className="mt-1 text-xs text-[color:var(--text-muted)]">Moving to next stage…</p>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
