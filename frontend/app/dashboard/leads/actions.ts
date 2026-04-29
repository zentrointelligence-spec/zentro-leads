"use server";

import { revalidatePath } from "next/cache";

import { leadsApi } from "@/lib/api";

/**
 * Kick off async lead generation for the given ICP id.
 * The backend returns immediately (202) — results appear as the background job completes.
 */
export async function generateLeads(
  icpId: string
): Promise<{ ok: boolean; message?: string; error?: string }> {
  try {
    const result = await leadsApi.generate(icpId);
    revalidatePath("/dashboard/leads");
    return { ok: true, message: result.message };
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Lead generation failed.";
    return { ok: false, error: msg };
  }
}

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
