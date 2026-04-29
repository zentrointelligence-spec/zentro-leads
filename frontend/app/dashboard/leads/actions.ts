"use server";

import { revalidatePath } from "next/cache";

import { leadsApi } from "@/lib/api";

/**
 * Suppress a lead (email/domain blocklist + status suppressed).
 */
export async function suppressLead(leadId: string): Promise<{ ok: boolean; error?: string }> {
  try {
    await leadsApi.suppress(leadId);
    revalidatePath("/dashboard/leads");
    return { ok: true };
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Could not suppress lead.";
    return { ok: false, error: msg };
  }
}

/**
 * Push / sync a single lead to ZIMS (backend POST /push-to-zims).
 */
export async function syncLeadToZims(leadId: string): Promise<{ ok: boolean; error?: string }> {
  try {
    await leadsApi.pushToZIMS(leadId);
    revalidatePath("/dashboard/leads");
    return { ok: true };
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "ZIMS sync failed.";
    return { ok: false, error: msg };
  }
}
