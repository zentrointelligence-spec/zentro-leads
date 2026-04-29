/**
 * lib/api.ts — Server-only API client for Zentro Leads
 * All calls go to FastAPI backend at port 8001
 * Never import this in client components
 */

import "server-only";
import { cookies } from "next/headers";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

// ── Types ─────────────────────────────────────────────────────

export type PlanTier = "free" | "starter" | "growth" | "pro" | "agency";
export type LeadTier = "hot" | "warm" | "potential" | "cold";
export type LeadStatus =
  | "new"
  | "contacted"
  | "replied"
  | "meeting"
  | "closed"
  | "lost"
  | "suppressed";
export type LeadSource = "google_maps" | "google_search" | "website" | "linkedin" | "job_board" | "manual" | "landing_page";

export interface User {
  id:                    string;
  email:                 string;
  full_name:             string;
  company_name:          string | null;
  phone:                 string | null;
  avatar_url:            string | null;
  plan:                  PlanTier;
  leads_used_this_month: number;
  leads_limit:           number;
  zims_linked:           boolean;
}

export interface ICP {
  id:               string;
  name:             string;
  description:      string;
  industries:       string[];
  job_titles:       string[];
  seniority_levels: string[];
  company_sizes:    string[];
  locations:        string[];
  keywords:         string[];
  intent_signals:   string[];
  search_queries:   string[];
  total_leads_generated: number;
  conversion_rate:  number;
  is_active:        boolean;
  created_at:       string;
}

export interface Company {
  id:             string;
  name:           string;
  domain:         string | null;
  website:        string | null;
  industry:       string | null;
  employee_range: string | null;
  city:           string | null;
  country:        string | null;
  phone:          string | null;
  whatsapp:       string | null;
  is_hiring:      boolean;
  in_the_news:    boolean;
  funding_stage:  string | null;
  google_rating:  number | null;
}

export interface Lead {
  id:             string;
  lead_score:     number;
  lead_tier:      LeadTier;
  status:         LeadStatus;
  source:         LeadSource | null;
  intent_signals: string[];
  score_breakdown: Record<string, unknown>;
  ai_whatsapp_msg:  string | null;
  ai_email_subject: string | null;
  ai_email_body:    string | null;
  ai_linkedin_note: string | null;
  outreach_sent:  boolean;
  notes:          string | null;
  follow_up_date: string | null;
  zims_lead_id:   string | null;
  zims_pushed_at: string | null;
  created_at:     string;
  person: {
    id:              string;
    full_name:       string;
    job_title:       string | null;
    email:           string | null;
    email_verified:  boolean;
    email_confidence:number;
    phone:           string | null;
    whatsapp:        string | null;
    linkedin_url:    string | null;
  } | null;
  company: Company | null;
}

export interface PaginatedLeads {
  items:    Lead[];
  total:    number;
  page:     number;
  per_page: number;
  pages:    number;
}

export interface LeadStats {
  hot: number;
  warm: number;
  potential: number;
  cold: number;
  total: number;
  used_this_month: number;
  limit: number;
  limit_percentage: number;
}

// ── Base fetcher ──────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const cookieStore = await cookies();
  const session = cookieStore.get("zentro_session")?.value;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(session ? { Cookie: `zentro_session=${session}` } : {}),
        ...(options.headers ?? {}),
      },
      cache: "no-store",
    });
  } finally {
    clearTimeout(timeout);
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail ?? `API error ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────

export const authApi = {
  me: () => apiFetch<User>("/api/v1/auth/me"),
};

// ── ICP ───────────────────────────────────────────────────────

export const icpApi = {
  list: () =>
    apiFetch<ICP[]>("/api/v1/icp/"),

  get: (id: string) =>
    apiFetch<ICP>(`/api/v1/icp/${id}`),

  create: (body: { name: string; description: string }) =>
    apiFetch<ICP>("/api/v1/icp/", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  buildWithAI: (description: string) =>
    apiFetch<ICP>("/api/v1/icp/build", {
      method: "POST",
      body: JSON.stringify({ description }),
    }),

  delete: (id: string) =>
    apiFetch<{ message: string }>(`/api/v1/icp/${id}`, {
      method: "DELETE",
    }),
};

// ── Leads ─────────────────────────────────────────────────────

export const leadsApi = {
  stats: () => apiFetch<LeadStats>("/api/v1/leads/stats"),

  list: (params?: {
    page?:         number;
    per_page?:     number;
    tier?:         LeadTier;
    status?:       LeadStatus;
    icp_id?:       string;
    search?:       string;
    has_email?:    boolean;
    zims_synced?:  boolean;
  }) => {
    const entries = Object.entries(params ?? {}).filter(([, v]) => v !== undefined);
    const qs = new URLSearchParams(
      entries.map(([k, v]) => [k, String(v)])
    ).toString();
    return apiFetch<PaginatedLeads>(`/api/v1/leads/?${qs}`);
  },

  get: (id: string) =>
    apiFetch<Lead>(`/api/v1/leads/${id}`),

  generate: (icpId: string) =>
    apiFetch<{ job_id: string; message: string }>("/api/v1/leads/generate", {
      method: "POST",
      body: JSON.stringify({ icp_id: icpId }),
    }),

  updateStatus: (id: string, status: LeadStatus) =>
    apiFetch<Lead>(`/api/v1/leads/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  addNote: (id: string, note: string) =>
    apiFetch<Lead>(`/api/v1/leads/${id}/note`, {
      method: "PATCH",
      body: JSON.stringify({ note }),
    }),

  pushToZIMS: (id: string) =>
    apiFetch<{ message: string; zims_lead_id: string }>(
      `/api/v1/leads/${id}/push-to-zims`,
      { method: "POST" }
    ),

  suppress: (id: string) =>
    apiFetch<{ message: string }>(`/api/v1/leads/${id}/suppress`, {
      method: "POST",
    }),

  exportCSV: (filters?: Record<string, string>) =>
    apiFetch<{ download_url: string }>("/api/v1/leads/export/csv", {
      method: "POST",
      body: JSON.stringify(filters ?? {}),
    }),

  nlSearch: (query: string) =>
    apiFetch<Lead[]>("/api/v1/leads/search/nl", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
};
