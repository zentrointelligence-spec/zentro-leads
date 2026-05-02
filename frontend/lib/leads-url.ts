/**
 * URL query helpers for the ZLIS leads dashboard.
 */

export type LeadsViewMode = "table" | "kanban";

export interface ParsedLeadsQuery {
  page: number;
  per_page: number;
  tier?: string;
  status?: string;
  search?: string;
  has_email?: boolean;
  zims_synced?: boolean;
  min_icp_match?: number;
  view: LeadsViewMode;
}

function first(v: string | string[] | undefined): string | undefined {
  if (Array.isArray(v)) return v[0];
  return v;
}

/**
 * Parse Next.js ``searchParams`` into a typed leads query object.
 */
export function parseLeadsQuery(
  searchParams: Record<string, string | string[] | undefined>
): ParsedLeadsQuery {
  const g = (k: string) => first(searchParams[k]);

  const page = Math.max(1, Number(g("page") || 1));
  const per_page = Math.min(100, Math.max(1, Number(g("per_page") || 20)));
  const he = g("has_email");
  const zm = g("zims");
  const icpMin = g("icp_min");
  const view = g("view") === "table" ? "table" : "kanban";

  // Default to 70% ICP match filter; "0" means show all
  const min_icp_match = icpMin === "0" ? 0 : icpMin ? Number(icpMin) : 70;

  return {
    page,
    per_page,
    tier: g("tier") || undefined,
    status: g("status") || undefined,
    search: g("search") || undefined,
    has_email: he === "true" ? true : he === "false" ? false : undefined,
    zims_synced: zm === "true" ? true : zm === "false" ? false : undefined,
    min_icp_match,
    view,
  };
}

/**
 * Serialize query object for ``router.push`` / links.
 */
export function stringifyLeadsQuery(q: ParsedLeadsQuery): string {
  const p = new URLSearchParams();
  p.set("page", String(q.page));
  p.set("per_page", String(q.per_page));
  p.set("view", q.view);
  if (q.tier) p.set("tier", q.tier);
  if (q.status) p.set("status", q.status);
  if (q.search) p.set("search", q.search);
  if (q.has_email === true) p.set("has_email", "true");
  if (q.has_email === false) p.set("has_email", "false");
  if (q.zims_synced === true) p.set("zims", "true");
  if (q.zims_synced === false) p.set("zims", "false");
  if (q.min_icp_match !== undefined) p.set("icp_min", String(q.min_icp_match));
  return p.toString();
}
