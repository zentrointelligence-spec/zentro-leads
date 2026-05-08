"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/cn";
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  usePipelineStore,
  type PipelineLead,
  type PipelineStage,
} from "@/lib/pipeline-store";
import {
  GripVertical,
  MoreHorizontal,
  ArrowRight,
  Mail,
  Phone,
  Trophy,
  RefreshCcw,
  Loader2,
  InboxIcon,
} from "lucide-react";
import { toast } from "sonner";

// ── Column config — must match backend PipelineStageName ──────────────────────

const COLUMNS: { id: PipelineStage; label: string; color: string; dot: string }[] = [
  { id: "new",         label: "New Lead",    color: "border-blue-400/30 bg-blue-400/5",    dot: "bg-blue-400" },
  { id: "contacted",   label: "Contacted",   color: "border-amber-400/30 bg-amber-400/5",  dot: "bg-amber-400" },
  { id: "qualified",   label: "Qualified",   color: "border-orange-400/30 bg-orange-400/5",dot: "bg-orange-400" },
  { id: "proposal",    label: "Proposal",    color: "border-violet-400/30 bg-violet-400/5",dot: "bg-violet-400" },
  { id: "closed_won",  label: "Closed Won",  color: "border-emerald-400/30 bg-emerald-400/5", dot: "bg-emerald-400" },
  { id: "closed_lost", label: "Closed Lost", color: "border-slate-400/30 bg-slate-400/5",  dot: "bg-slate-500" },
];

// ── Tier badge ────────────────────────────────────────────────────────────────

function TierBadge({ tier }: { tier: PipelineLead["tier"] }) {
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-black",
      tier === "HOT"       && "bg-red-500/15 text-red-300",
      tier === "WARM"      && "bg-amber-500/15 text-amber-300",
      tier === "POTENTIAL" && "bg-blue-500/15 text-blue-300",
      tier === "COLD"      && "bg-slate-500/15 text-slate-400",
    )}>
      {tier}
    </span>
  );
}

// ── Loading skeleton card ─────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-white/[0.05] bg-[#0d1425] p-4 space-y-2 animate-pulse">
      <div className="h-3 w-3/4 rounded bg-white/[0.06]" />
      <div className="h-2 w-1/2 rounded bg-white/[0.04]" />
      <div className="mt-3 h-2 w-1/3 rounded bg-white/[0.04]" />
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyColumn() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 py-10 text-center">
      <InboxIcon className="h-5 w-5 text-slate-700 mb-2" />
      <p className="text-xs text-slate-600">No leads here yet</p>
    </div>
  );
}

// ── Sortable lead card ────────────────────────────────────────────────────────

function LeadCard({ lead, overlay = false }: { lead: PipelineLead; overlay?: boolean }) {
  const { moveStage } = usePipelineStore();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: lead.id });

  const stages = COLUMNS.map((c) => c.id);
  const currentIdx = stages.indexOf(lead.stage);
  const nextStage  = stages[currentIdx + 1] as PipelineStage | undefined;

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "group rounded-xl border border-white/[0.08] bg-[#0d1425] p-4 shadow-sm select-none",
        isDragging && !overlay && "opacity-30",
        overlay && "shadow-[0_24px_60px_rgba(0,0,0,0.4)] rotate-1"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-black text-white">{lead.name}</div>
          <div className="truncate text-xs text-slate-500">{lead.company || "—"}</div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <TierBadge tier={lead.tier} />
          <span className="text-sm font-black text-white">{lead.score}</span>
          <button
            {...attributes}
            {...listeners}
            className="cursor-grab touch-none text-slate-600 hover:text-slate-400"
            aria-label="Drag handle"
          >
            <GripVertical className="h-4 w-4" />
          </button>
        </div>
      </div>

      {lead.productType && (
        <div className="mt-2 text-[10px] font-medium text-slate-600">{lead.productType}</div>
      )}

      <div className="mt-3 flex items-center gap-3 text-slate-600">
        {lead.email && <Mail className="h-3.5 w-3.5" />}
        {lead.phone && <Phone className="h-3.5 w-3.5" />}
        {lead.stage === "closed_won" && <Trophy className="h-3.5 w-3.5 text-emerald-500" />}
      </div>

      <div className="mt-3 flex items-center justify-between">
        <span className="text-[10px] text-slate-600">
          {new Date(lead.pushedAt).toLocaleDateString("en-MY", { day: "numeric", month: "short" })}
        </span>
        {nextStage && (
          <button
            type="button"
            onClick={() => {
              void moveStage(lead.id, nextStage);
              toast.success(`Moved to ${COLUMNS.find(c => c.id === nextStage)?.label}`);
            }}
            className="flex items-center gap-1 rounded-lg bg-white/[0.05] px-2 py-1 text-[10px] font-bold text-slate-400 transition hover:bg-orange-500/15 hover:text-orange-300"
          >
            {COLUMNS.find(c => c.id === nextStage)?.label} <ArrowRight className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  );
}

// ── Kanban column ─────────────────────────────────────────────────────────────

function KanbanColumn({
  label,
  color,
  dot,
  leads,
  loading,
}: (typeof COLUMNS)[0] & { leads: PipelineLead[]; loading: boolean }) {
  return (
    <div className={cn("flex flex-col rounded-2xl border p-4 min-w-[220px]", color)}>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={cn("h-2 w-2 rounded-full", dot)} />
          <span className="text-sm font-black text-white">{label}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-white/10 px-2 py-0.5 text-xs font-bold text-slate-400">
            {loading ? "…" : leads.length}
          </span>
          <button type="button" className="text-slate-600 hover:text-slate-400">
            <MoreHorizontal className="h-4 w-4" />
          </button>
        </div>
      </div>

      <SortableContext items={leads.map((l) => l.id)} strategy={verticalListSortingStrategy}>
        <div className="min-h-[120px] space-y-3">
          {loading ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : (
            <AnimatePresence>
              {leads.length === 0 ? (
                <EmptyColumn />
              ) : (
                leads.map((lead) => (
                  <motion.div
                    key={lead.id}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                  >
                    <LeadCard lead={lead} />
                  </motion.div>
                ))
              )}
            </AnimatePresence>
          )}
        </div>
      </SortableContext>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PipelinePage() {
  const { leads, loading, fetchPipeline, moveStage, getByStage } = usePipelineStore();
  const [activeId, setActiveId] = useState<string | null>(null);

  // Fetch from server on mount
  useEffect(() => {
    void fetchPipeline();
  }, [fetchPipeline]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const activeLead = activeId ? leads.find((l) => l.id === activeId) : null;

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);
    if (!over) return;

    const overId       = over.id as string;
    const targetColumn = COLUMNS.find((c) => c.id === overId);
    const targetLead   = leads.find((l) => l.id === overId);

    if (targetColumn && targetColumn.id !== leads.find(l => l.id === active.id)?.stage) {
      void moveStage(active.id as string, targetColumn.id);
      toast.success(`Moved to ${targetColumn.label}`);
    } else if (targetLead && targetLead.stage !== leads.find(l => l.id === active.id)?.stage) {
      void moveStage(active.id as string, targetLead.stage);
    }
  };

  const totalLeads  = leads.length;
  const closedWon   = getByStage("closed_won").length;
  const closedLost  = getByStage("closed_lost").length;
  const closedTotal = closedWon + closedLost;
  const convRate    = closedTotal > 0 ? Math.round((closedWon / closedTotal) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Header row */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-foreground-primary">Pipeline</h1>
          <p className="mt-1 text-sm text-foreground-muted">
            Drag deals between stages or use the quick-move buttons. Push leads from the Leads tab.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="rounded-xl border border-white/[0.08] bg-card-bg px-4 py-2 text-center">
            <div className="text-lg font-black text-foreground-primary">{loading ? "…" : totalLeads}</div>
            <div className="text-[10px] font-medium text-foreground-muted">Total</div>
          </div>
          <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/5 px-4 py-2 text-center">
            <div className="text-lg font-black text-emerald-400">{loading ? "…" : `${convRate}%`}</div>
            <div className="text-[10px] font-medium text-foreground-muted">Win Rate</div>
          </div>
          <button
            type="button"
            onClick={() => void fetchPipeline()}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-card-bg px-3 py-2 text-xs font-medium text-foreground-muted hover:text-foreground-primary transition-colors disabled:opacity-50"
            title="Refresh pipeline"
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCcw className="h-3.5 w-3.5" />
            )}
            Refresh
          </button>
        </div>
      </div>

      {/* Kanban board */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="overflow-x-auto pb-4">
          <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${COLUMNS.length}, minmax(220px, 1fr))` }}>
            {COLUMNS.map((col) => (
              <KanbanColumn
                key={col.id}
                {...col}
                leads={getByStage(col.id)}
                loading={loading}
              />
            ))}
          </div>
        </div>

        <DragOverlay>
          {activeLead && <LeadCard lead={activeLead} overlay />}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
