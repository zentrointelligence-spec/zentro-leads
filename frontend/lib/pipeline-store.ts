/**
 * Client-side pipeline store (Zustand) — server-backed.
 *
 * Server is the source of truth. Local Zustand state is used for
 * optimistic updates and instant UI feedback. Every mutation is
 * immediately reflected locally and synced to the backend async.
 *
 * PipelineLead.id = pipeline entry ID assigned by the server.
 * PipelineLead.sourceLeadId = original lead UUID from zl_leads.
 */
import { create } from "zustand";

export type PipelineStage =
  | "new"
  | "contacted"
  | "qualified"
  | "proposal"
  | "closed_won"
  | "closed_lost";

export interface PipelineLead {
  /** Pipeline entry ID (server-assigned UUID). Used for PATCH/DELETE calls. */
  id: string;
  name: string;
  company: string;
  email?: string;
  phone?: string;
  score: number;
  tier: "HOT" | "WARM" | "POTENTIAL" | "COLD";
  stage: PipelineStage;
  pushedAt: string;
  productType?: string;
  /** Original lead UUID from zl_leads (used for duplicate detection). */
  sourceLeadId?: string;
}

interface PipelineState {
  leads: PipelineLead[];
  loading: boolean;
  error: string | null;

  /** Fetch all pipeline entries from the server and replace local state. */
  fetchPipeline: () => Promise<void>;

  /**
   * Add a lead to the pipeline.
   * Accepts the same shape as before so lead-table-view.tsx needs no changes.
   * Calls POST /api/v1/pipeline/ and replaces the optimistic entry with the
   * real server entry (which has the canonical pipeline entry ID).
   */
  pushLead: (lead: Omit<PipelineLead, "stage" | "pushedAt">) => Promise<void>;

  /**
   * Move a pipeline entry to a new stage.
   * Optimistically updates local state, then PATCHes the server.
   */
  moveStage: (id: string, stage: PipelineStage) => Promise<void>;

  /** Remove a pipeline entry from the server and local state. */
  removeLead: (id: string) => Promise<void>;

  /** Filter local leads by stage. */
  getByStage: (stage: PipelineStage) => PipelineLead[];
}

// ── API helpers (client-side, credentials: include) ───────────────────────────

async function apiGet(): Promise<{ entries: PipelineLead[] }> {
  const res = await fetch("/api/v1/pipeline/", { credentials: "include" });
  if (!res.ok) throw new Error(`Pipeline fetch failed: ${res.status}`);
  const data = await res.json();
  return {
    entries: (data.entries ?? []).map(serverEntryToLocal),
  };
}

async function apiAdd(
  lead_id: string,
  stage: PipelineStage
): Promise<PipelineLead> {
  const res = await fetch("/api/v1/pipeline/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ lead_id, stage }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed" }));
    throw new Error(err.detail ?? "Add to pipeline failed");
  }
  return serverEntryToLocal(await res.json());
}

async function apiMove(id: string, stage: PipelineStage): Promise<PipelineLead> {
  const res = await fetch(`/api/v1/pipeline/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ stage }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed" }));
    throw new Error(err.detail ?? "Move failed");
  }
  return serverEntryToLocal(await res.json());
}

async function apiRemove(id: string): Promise<void> {
  const res = await fetch(`/api/v1/pipeline/${id}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok && res.status !== 204) {
    const err = await res.json().catch(() => ({ detail: "Failed" }));
    throw new Error(err.detail ?? "Remove failed");
  }
}

/** Map a raw server pipeline entry to the local PipelineLead shape. */
function serverEntryToLocal(e: Record<string, unknown>): PipelineLead {
  const rawTier = String(e.tier ?? "").toUpperCase();
  const tier = (["HOT", "WARM", "POTENTIAL", "COLD"].includes(rawTier)
    ? rawTier
    : "POTENTIAL") as PipelineLead["tier"];

  return {
    id:          String(e.id),
    name:        String(e.name ?? "Unknown"),
    company:     String(e.company ?? ""),
    email:       e.email ? String(e.email) : undefined,
    phone:       e.phone ? String(e.phone) : undefined,
    score:       typeof e.score === "number" ? e.score : 0,
    tier,
    stage:       (e.stage as PipelineStage) ?? "new",
    pushedAt:    String(e.created_at ?? new Date().toISOString()),
    productType: e.product_type ? String(e.product_type) : undefined,
    sourceLeadId: String(e.lead_id),
  };
}

// ── Store ─────────────────────────────────────────────────────────────────────

export const usePipelineStore = create<PipelineState>()((set, get) => ({
  leads:   [],
  loading: false,
  error:   null,

  fetchPipeline: async () => {
    set({ loading: true, error: null });
    try {
      const { entries } = await apiGet();
      set({ leads: entries, loading: false });
    } catch (err) {
      set({ loading: false, error: String(err) });
    }
  },

  pushLead: async (lead) => {
    // Skip if already in pipeline (check by sourceLeadId)
    const existing = get().leads.find(
      (l) => l.sourceLeadId === lead.sourceLeadId || l.id === lead.id
    );
    if (existing) return;

    // Optimistic insert — use a temp id until server responds
    const TEMP_ID = `temp-${lead.id}`;
    const optimistic: PipelineLead = {
      ...lead,
      id:      TEMP_ID,
      stage:   "new",
      pushedAt: new Date().toISOString(),
    };
    set((state) => ({ leads: [...state.leads, optimistic] }));

    try {
      // sourceLeadId is the original lead UUID we send to the server
      const leadId = lead.sourceLeadId ?? lead.id;
      const serverEntry = await apiAdd(leadId, "new");
      // Replace optimistic entry with real server entry
      set((state) => ({
        leads: state.leads.map((l) => (l.id === TEMP_ID ? serverEntry : l)),
      }));
    } catch {
      // Rollback on failure
      set((state) => ({
        leads: state.leads.filter((l) => l.id !== TEMP_ID),
        error: "Failed to add lead to pipeline",
      }));
    }
  },

  moveStage: async (id, stage) => {
    // Optimistic update
    const prev = get().leads.find((l) => l.id === id);
    set((state) => ({
      leads: state.leads.map((l) => (l.id === id ? { ...l, stage } : l)),
    }));

    try {
      const updated = await apiMove(id, stage);
      // Confirm with server response
      set((state) => ({
        leads: state.leads.map((l) => (l.id === id ? updated : l)),
      }));
    } catch {
      // Rollback
      if (prev) {
        set((state) => ({
          leads: state.leads.map((l) => (l.id === id ? prev : l)),
          error: "Move failed — changes reverted",
        }));
      }
    }
  },

  removeLead: async (id) => {
    const prev = get().leads;
    set((state) => ({ leads: state.leads.filter((l) => l.id !== id) }));
    try {
      await apiRemove(id);
    } catch {
      set({ leads: prev, error: "Remove failed — changes reverted" });
    }
  },

  getByStage: (stage) => get().leads.filter((l) => l.stage === stage),
}));
