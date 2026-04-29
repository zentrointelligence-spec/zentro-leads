"use client";

import { memo, useCallback, useEffect, useMemo, useState } from "react";
import {
  closestCorners,
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
  type DropAnimation,
} from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical } from "lucide-react";

import type { Lead, LeadTier } from "@/lib/api";
import { cn } from "@/lib/cn";

import { LeadCard } from "./LeadCard";

type ColumnTier = Extract<LeadTier, "hot" | "warm" | "potential">;

function bucketLeads(leads: Lead[]): Record<ColumnTier, Lead[]> {
  const hot: Lead[] = [];
  const warm: Lead[] = [];
  const potential: Lead[] = [];
  for (const l of leads) {
    if (l.lead_tier === "hot") hot.push(l);
    else if (l.lead_tier === "warm") warm.push(l);
    else potential.push(l);
  }
  return { hot, warm, potential };
}

/**
 * Placeholder for future PATCH when API supports persisting pipeline tier from Kanban.
 */
function persistKanbanTierPreview(leadId: string, tier: LeadTier): void {
  if (process.env.NODE_ENV === "development") {
    console.debug("[ZLIS] Kanban tier (UI preview; persist API pending)", { leadId, tier });
  }
}

const dropAnimation: DropAnimation = {
  duration: 220,
  easing: "cubic-bezier(0.2, 0.8, 0.2, 1)",
};

interface Props {
  leads: Lead[];
  onOpen: (lead: Lead) => void;
}

/**
 * Three-column pipeline with drag-and-drop tier changes (client-only until API supports PATCH tier).
 */
export function LeadKanban({ leads, onOpen }: Props) {
  const [columns, setColumns] = useState(() => bucketLeads(leads));
  const [activeId, setActiveId] = useState<string | null>(null);

  const snapshot = useMemo(
    () => leads.map((l) => `${l.id}:${l.lead_tier}`).join("|"),
    [leads]
  );

  useEffect(() => {
    setColumns(bucketLeads(leads));
  }, [snapshot, leads]);

  const flatTierById = useMemo(() => {
    const m = new Map<string, ColumnTier>();
    for (const tier of ["hot", "warm", "potential"] as const) {
      for (const l of columns[tier]) m.set(l.id, tier);
    }
    return m;
  }, [columns]);

  const resolveTargetTier = useCallback(
    (overId: string): ColumnTier | null => {
      if (overId === "col-hot") return "hot";
      if (overId === "col-warm") return "warm";
      if (overId === "col-potential") return "potential";
      return flatTierById.get(overId) ?? null;
    },
    [flatTierById]
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  );

  function handleDragStart(e: DragStartEvent) {
    setActiveId(String(e.active.id));
  }

  function handleDragEnd(e: DragEndEvent) {
    const { active, over } = e;
    setActiveId(null);
    if (!over) return;
    const target = resolveTargetTier(String(over.id));
    if (!target) return;
    const leadId = String(active.id);
    setColumns((prev) => {
      const flat = [...prev.hot, ...prev.warm, ...prev.potential];
      const lead = flat.find((l) => l.id === leadId);
      if (!lead) return prev;
      const newTier = target as LeadTier;
      const updated: Lead = { ...lead, lead_tier: newTier };
      const rest = flat.filter((l) => l.id !== leadId);
      persistKanbanTierPreview(leadId, newTier);
      return bucketLeads([...rest, updated]);
    });
  }

  const activeLead =
    activeId === null
      ? null
      : [...columns.hot, ...columns.warm, ...columns.potential].find((l) => l.id === activeId) ?? null;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="grid min-h-[420px] gap-4 md:grid-cols-3 md:gap-5">
        {(["hot", "warm", "potential"] as const).map((tier) => (
          <KanbanColumnMemo key={tier} tier={tier} leads={columns[tier]} onOpen={onOpen} />
        ))}
      </div>
      <DragOverlay dropAnimation={dropAnimation}>
        {activeLead ? (
          <div className="max-w-sm cursor-grabbing rounded-lg shadow-2xl shadow-black/50 ring-1 ring-white/[0.08]">
            <LeadCard lead={activeLead} onOpen={() => {}} />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

const KanbanColumnMemo = memo(function KanbanColumnMemo({
  tier,
  leads,
  onOpen,
}: {
  tier: ColumnTier;
  leads: Lead[];
  onOpen: (lead: Lead) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: `col-${tier}` });
  const title = tier === "hot" ? "HOT" : tier === "warm" ? "WARM" : "POTENTIAL";

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "relative flex min-h-[340px] flex-col rounded-lg border border-white/[0.06] bg-[#09090b]/50 shadow-md shadow-black/20 transition-[border-color,box-shadow,transform] duration-200 ease-out",
        isOver && "border-brand-blue/40 shadow-lg shadow-brand-blue/10 ring-1 ring-brand-blue/25"
      )}
    >
      <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-3">
        <span className="text-[12px] font-semibold tracking-tight text-zinc-200">
          {title}{" "}
          <span className="font-medium text-zinc-500">({leads.length})</span>
        </span>
      </div>
      <div className="relative flex flex-1 flex-col gap-2 p-2.5">
        {leads.length === 0 ? (
          <p className="py-12 text-center text-[12px] text-zinc-600">Drop leads here</p>
        ) : (
          leads.map((lead) => <KanbanDraggableMemo key={lead.id} lead={lead} onOpen={onOpen} />)
        )}
      </div>
    </div>
  );
});

const KanbanDraggableMemo = memo(function KanbanDraggableMemo({
  lead,
  onOpen,
}: {
  lead: Lead;
  onOpen: (lead: Lead) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: lead.id });
  const style = transform ? { transform: CSS.Translate.toString(transform) } : undefined;

  return (
    <div ref={setNodeRef} style={style} className={cn("relative", isDragging && "opacity-[0.35]")}>
      <button
        type="button"
        className="absolute left-1.5 top-3 z-10 cursor-grab rounded-md p-1.5 text-zinc-600 touch-none transition-colors duration-150 hover:bg-white/[0.06] hover:text-zinc-300 active:cursor-grabbing"
        aria-label="Drag to change tier"
        {...listeners}
        {...attributes}
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <div className="pl-8">
        <LeadCard lead={lead} onOpen={onOpen} />
      </div>
    </div>
  );
});
