/**
 * Browser-side lead API helpers (same REST contract as FastAPI; proxied via Next rewrites).
 */

import type { Lead, LeadStatus } from "@/lib/api";

export async function patchLeadStatus(id: string, status: LeadStatus): Promise<Lead> {
  const res = await fetch(`/api/v1/leads/${id}/status`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<Lead>;
}
