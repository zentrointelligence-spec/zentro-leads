"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import type { Lead } from "@/lib/api";

import { suppressLead, syncLeadToZims } from "../actions";

export interface LeadsDashboardContextValue {
  pipelineLeads: Lead[];
  suppressLeadOptimistic: (lead: Lead) => Promise<boolean>;
  syncZimsOptimistic: (lead: Lead) => Promise<boolean>;
}

const LeadsDashboardContext = createContext<LeadsDashboardContextValue | null>(null);

interface ProviderProps {
  children: ReactNode;
  displayLeads: Lead[];
  onLeadSuppressed?: (leadId: string) => void;
}

/**
 * Optimistic pipeline actions + derived lead list for table, Kanban, and drawer.
 */
export function LeadsDashboardProvider({
  children,
  displayLeads,
  onLeadSuppressed,
}: ProviderProps) {
  const router = useRouter();
  const [suppressedIds, setSuppressedIds] = useState<Set<string>>(() => new Set());
  const [zimsOverride, setZimsOverride] = useState<
    Record<string, Pick<Lead, "zims_lead_id" | "zims_pushed_at">>
  >({});

  const pipelineLeads = useMemo(() => {
    return displayLeads
      .filter((l) => !suppressedIds.has(l.id))
      .map((l) => {
        const o = zimsOverride[l.id];
        return o ? { ...l, ...o } : l;
      });
  }, [displayLeads, suppressedIds, zimsOverride]);

  const suppressLeadOptimistic = useCallback(
    async (lead: Lead): Promise<boolean> => {
      setSuppressedIds((s) => new Set(s).add(lead.id));
      try {
        const r = await suppressLead(lead.id);
        if (!r.ok) {
          setSuppressedIds((s) => {
            const n = new Set(s);
            n.delete(lead.id);
            return n;
          });
          toast.error(r.error ?? "Suppress failed.");
          return false;
        }
        toast.success("Lead suppressed.");
        onLeadSuppressed?.(lead.id);
        await router.refresh();
        setSuppressedIds(new Set());
        return true;
      } catch (e) {
        setSuppressedIds((s) => {
          const n = new Set(s);
          n.delete(lead.id);
          return n;
        });
        toast.error(e instanceof Error ? e.message : "Suppress failed.");
        return false;
      }
    },
    [onLeadSuppressed, router]
  );

  const syncZimsOptimistic = useCallback(
    async (lead: Lead): Promise<boolean> => {
      const pendingId = `pending:${lead.id.slice(0, 8)}`;
      setZimsOverride((o) => ({
        ...o,
        [lead.id]: {
          zims_lead_id: pendingId,
          zims_pushed_at: new Date().toISOString(),
        },
      }));
      try {
        const r = await syncLeadToZims(lead.id);
        if (!r.ok) {
          setZimsOverride((o) => {
            const n = { ...o };
            delete n[lead.id];
            return n;
          });
          toast.error(r.error ?? "ZIMS sync failed.");
          return false;
        }
        toast.success("ZIMS sync requested.");
        await router.refresh();
        setZimsOverride({});
        return true;
      } catch (e) {
        setZimsOverride((o) => {
          const n = { ...o };
          delete n[lead.id];
          return n;
        });
        toast.error(e instanceof Error ? e.message : "ZIMS sync failed.");
        return false;
      }
    },
    [router]
  );

  const value = useMemo(
    () => ({
      pipelineLeads,
      suppressLeadOptimistic,
      syncZimsOptimistic,
    }),
    [pipelineLeads, suppressLeadOptimistic, syncZimsOptimistic]
  );

  return (
    <LeadsDashboardContext.Provider value={value}>{children}</LeadsDashboardContext.Provider>
  );
}

export function useLeadsDashboardActions(): LeadsDashboardContextValue {
  const ctx = useContext(LeadsDashboardContext);
  if (!ctx) {
    throw new Error("useLeadsDashboardActions must be used within LeadsDashboardProvider");
  }
  return ctx;
}
