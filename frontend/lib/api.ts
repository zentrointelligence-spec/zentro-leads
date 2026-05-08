/**
 * lib/api.ts — Server-only API client for Zentro Leads
 * All calls go to FastAPI backend at port 8001
 * Never import this in client components
 */

import "server-only";
import { cookies } from "next/headers";
import { readJsonBody, detailFromUnknownJson } from "@/lib/read-json-response";

// exportCSV is the one function intentionally excluded from the server-only
// constraint — it must run in the browser to trigger a file download.
// It is exported separately and must only be called from client components.

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

// ── Types ─────────────────────────────────────────────────────

export type PlanTier = "free" | "starter" | "growth" | "pro" | "agency";
export type LeadTier = "hot" | "warm" | "potential" | "cold";
export type LeadStatus =
  | "new"
  | "viewed"
  | "contacted"
  | "replied"
  | "meeting"
  | "closed"
  | "won"
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
  /** Present on API responses after RBAC rollout; treat missing as `"agent"`. */
  role?:                 "agent" | "owner" | "admin";
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
  ssm_verified:   boolean;
  years_in_business: string | null;
  revenue_estimate: string | null;
  is_malaysian_company: boolean;
  decision_maker_name: string | null;
  decision_maker_title: string | null;
  linkedin_url:   string | null;
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
  icp_match_score: number;
  icp_verdict:    string | null;
  icp_reason:     string | null;
  recommended_product: string | null;
  lead_type:      string | null;
  insurance_type: string | null;
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

  const parsed = await readJsonBody<unknown>(res);

  if (!res.ok) {
    if (parsed.ok) {
      const detail = detailFromUnknownJson(parsed.data);
      if (detail) throw new Error(detail);
      throw new Error(`API error ${res.status}`);
    }
    throw new Error(
      parsed.bodyPreview.length > 0
        ? `${parsed.bodyPreview}${parsed.bodyPreview.length >= 240 ? "…" : ""}`
        : `API error ${res.status}`
    );
  }

  if (!parsed.ok) {
    throw new Error(
      `Invalid JSON from API (${res.status}): ${parsed.bodyPreview}`
    );
  }

  return parsed.data as T;
}

// ── Auth ──────────────────────────────────────────────────────

export const authApi = {
  me: () => apiFetch<User>("/api/v1/auth/me"),
};

// ── ICP ───────────────────────────────────────────────────────

export interface ICPListResponse {
  items: ICP[];
  total: number;
}

export const icpApi = {
  // Returns { items, total } — not ICP[] directly
  list: () =>
    apiFetch<ICPListResponse>("/api/v1/icp/"),

  get: (id: string) =>
    apiFetch<ICP>(`/api/v1/icp/${id}`),

  create: (body: {
    name: string;
    description: string;
    industries?: string[];
    job_titles?: string[];
    seniority_levels?: string[];
    company_sizes?: string[];
    locations?: string[];
    keywords?: string[];
    intent_signals?: string[];
    search_queries?: string[];
  }) =>
    apiFetch<ICP>("/api/v1/icp/", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  buildWithAI: (description: string) =>
    apiFetch<ICP>("/api/v1/icp/build", {
      method: "POST",
      body: JSON.stringify({ description }),
    }),

  update: (id: string, body: Partial<ICP>) =>
    apiFetch<ICP>(`/api/v1/icp/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  // Returns 204 No Content — handle as void
  delete: async (id: string): Promise<void> => {
    const cookieStore = await cookies();
    const session = cookieStore.get("zentro_session")?.value;
    const res = await fetch(`${BASE}/api/v1/icp/${id}`, {
      method: "DELETE",
      headers: session ? { Cookie: `zentro_session=${session}` } : {},
      cache: "no-store",
    });
    if (!res.ok && res.status !== 204) {
      const parsed = await readJsonBody<{ detail?: string }>(res);
      if (parsed.ok) {
        const detail = detailFromUnknownJson(parsed.data);
        throw new Error(detail || `Delete failed ${res.status}`);
      }
      throw new Error(parsed.bodyPreview || `Delete failed ${res.status}`);
    }
  },
};

// ── Leads ─────────────────────────────────────────────────────

export const leadsApi = {
  stats: () => apiFetch<LeadStats>("/api/v1/leads/stats"),

  list: (params?: {
    page?:           number;
    per_page?:       number;
    tier?:           LeadTier;
    status?:         LeadStatus;
    icp_id?:         string;
    search?:         string;
    has_email?:      boolean;
    zims_synced?:    boolean;
    min_icp_match?:  number;
    lead_type?:      "b2b" | "b2c";
    market?:         "malaysia" | "india";
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
    apiFetch<{ message: string; estimated_seconds?: number; icp_name?: string }>("/api/v1/leads/generate", {
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

  // Triggers a browser CSV download — must be called from a client component.
  // Backend returns a raw StreamingResponse (Content-Disposition: attachment),
  // NOT JSON. Uses credentials: "include" so the browser sends the session cookie.
  exportCSV: async (filters?: Record<string, string>): Promise<void> => {
    const res = await fetch(`${BASE}/api/v1/leads/export/csv`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(filters ?? {}),
    });
    if (!res.ok) {
      const parsed = await readJsonBody<{ detail?: string }>(res);
      if (parsed.ok) {
        const detail = detailFromUnknownJson(parsed.data);
        throw new Error(detail || `Export failed ${res.status}`);
      }
      throw new Error(parsed.bodyPreview || `Export failed ${res.status}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "zentro-leads.csv";
    a.click();
    URL.revokeObjectURL(url);
  },

  nlSearch: (query: string) =>
    apiFetch<Lead[]>("/api/v1/leads/search/nl", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
};

// ── Billing ───────────────────────────────────────────────────

export type BillingPlan = "starter" | "growth" | "pro" | "agency";

export const billingApi = {
  /**
   * Create a Stripe Checkout session for the given plan.
   * Returns a checkout_url the caller should redirect to.
   * Server-only — call from a Server Action or API route handler.
   */
  createCheckout: (plan: BillingPlan) =>
    apiFetch<{ checkout_url: string }>("/api/v1/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan }),
    }),

  /**
   * Create a Billplz FPX bill for Malaysian customers.
   * Returns fpx_url — redirect user's browser to this URL to complete FPX payment.
   * Server-only — call from a Server Action or API route handler.
   */
  createFpxCheckout: (plan: BillingPlan, phone: string) =>
    apiFetch<{ fpx_url: string; bill_id: string }>("/api/v1/billing/checkout/fpx", {
      method: "POST",
      body: JSON.stringify({ plan, phone }),
    }),

  /**
   * Create a Razorpay order for Indian UPI / card / NetBanking payment.
   * Returns order details to pass into the Razorpay.js modal.
   */
  createUpiOrder: (plan: BillingPlan) =>
    apiFetch<{
      order_id:     string;
      amount:       number;
      currency:     string;
      razorpay_key: string;
    }>("/api/v1/billing/checkout/upi", {
      method: "POST",
      body: JSON.stringify({ plan }),
    }),

  /**
   * Verify a Razorpay payment signature and activate the plan.
   * Called by the frontend after the Razorpay.js handler callback fires.
   */
  verifyRazorpayPayment: (data: {
    order_id:   string;
    payment_id: string;
    signature:  string;
    plan:       BillingPlan;
  }) =>
    apiFetch<{ success: boolean; plan: string }>("/api/v1/billing/razorpay/verify", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// ── Pipeline ──────────────────────────────────────────────────

export type PipelineStage =
  | "new"
  | "contacted"
  | "qualified"
  | "proposal"
  | "closed_won"
  | "closed_lost";

export interface PipelineEntry {
  id:           string;   // pipeline entry ID (server-assigned)
  stage:        PipelineStage;
  notes:        string | null;
  moved_at:     string | null;
  created_at:   string | null;
  lead_id:      string;
  name:         string;
  company:      string | null;
  email:        string | null;
  phone:        string | null;
  score:        number | null;
  tier:         string | null;
  product_type: string | null;
}

export interface PipelineListResponse {
  entries: PipelineEntry[];
  total:   number;
}

export const pipelineApi = {
  get: () =>
    apiFetch<PipelineListResponse>("/api/v1/pipeline/"),

  add: (lead_id: string, stage: PipelineStage = "new", notes?: string) =>
    apiFetch<PipelineEntry>("/api/v1/pipeline/", {
      method: "POST",
      body: JSON.stringify({ lead_id, stage, notes }),
    }),

  move: (id: string, stage: PipelineStage, notes?: string) =>
    apiFetch<PipelineEntry>(`/api/v1/pipeline/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ stage, notes }),
    }),

  remove: async (id: string): Promise<void> => {
    const cookieStore = await cookies();
    const session = cookieStore.get("zentro_session")?.value;
    const res = await fetch(`${BASE}/api/v1/pipeline/${id}`, {
      method: "DELETE",
      headers: session ? { Cookie: `zentro_session=${session}` } : {},
      cache: "no-store",
    });
    if (!res.ok && res.status !== 204) {
      const parsed = await readJsonBody<{ detail?: string }>(res);
      if (parsed.ok) {
        const detail = detailFromUnknownJson(parsed.data);
        throw new Error(detail || `Remove failed ${res.status}`);
      }
      throw new Error(parsed.bodyPreview || `Remove failed ${res.status}`);
    }
  },
};

// ── Admin API types ───────────────────────────────────────────

export interface AdminUserListItem {
  id:           string;
  email:        string;
  full_name:    string;
  company_name: string | null;
  role:         "agent" | "owner" | "admin";
  plan:         PlanTier;
  is_active:    boolean;
  lead_count:   number;
  icp_count:    number;
  created_at:   string;
  last_login:   string | null;
}

export interface AdminUserListResponse {
  items: AdminUserListItem[];
  total: number;
}

export interface UpdateUserRequest {
  role?:      "agent" | "owner" | "admin";
  plan?:      PlanTier;
  is_active?: boolean;
}

export interface PlatformStats {
  total_users:               number;
  active_users_today:        number;
  active_users_this_week:    number;
  total_leads_generated:     number;
  leads_generated_today:     number;
  leads_generated_this_week: number;
  total_b2b_leads:           number;
  total_b2c_leads:           number;
  hot_leads_total:           number;
  average_lead_score:        number;
  total_icps_created:        number;
  total_zims_pushes:         number;
  top_industries:            Array<{ industry: string; count: number }>;
  top_locations:             Array<{ city: string; count: number }>;
  revenue_this_month:        number | null;
}

export interface ActivityEvent {
  event_type:  string;
  user_email:  string | null;
  detail:      string;
  timestamp:   string | null;
}

export interface AgencyDetail {
  user:             AdminUserListItem;
  leads:            Array<{
    id: string;
    company_name: string;
    person_name: string;
    lead_score: number;
    lead_tier: string;
    status: string;
    lead_type: string;
    created_at: string | null;
  }>;
  icps:             Array<{
    id: string;
    name: string;
    industries: string[];
    locations: string[];
    created_at: string | null;
  }>;
  pipeline_summary: Record<string, number>;
  recent_activity:  Array<{
    event_type: string;
    old_value: string | null;
    new_value: string | null;
    note: string | null;
    created_at: string | null;
  }>;
}

export interface QualityReport {
  total_leads:           number;
  /** Percentage 0–100 */
  email_verified_pct:    number;
  /** Percentage 0–100 */
  phone_present_pct:     number;
  score_distribution:    { hot: number; warm: number; qualified: number; cold: number };
  avg_score_by_source:   Record<string, number>;
  /** Percentage 0–100 (share of leads implicated in duplicate person groups) */
  duplicate_rate:        number;
  leads_without_contact: number;
}

export interface ServiceHealth {
  status:     "healthy" | "ok" | "degraded" | "down";
  latency_ms: number | null;
  detail:     string | null;
}

export interface SystemHealth {
  postgresql:    ServiceHealth;
  redis:         ServiceHealth;
  elasticsearch: ServiceHealth;
  pinecone:      ServiceHealth;
  anthropic:     ServiceHealth;
  scheduler:     ServiceHealth;
  overall:       "ok" | "degraded" | "down";
}

// ── Admin API client ──────────────────────────────────────────

export const adminApi = {
  getStats: () =>
    apiFetch<PlatformStats>("/api/v1/admin/stats"),

  getActivity: () =>
    apiFetch<ActivityEvent[]>("/api/v1/admin/activity"),

  getUsers: (params?: {
    search?:    string;
    role?:      string;
    plan?:      string;
    is_active?: boolean;
    limit?:     number;
    offset?:    number;
  }) => {
    const entries = Object.entries(params ?? {}).filter(([, v]) => v !== undefined);
    const qs = new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
    return apiFetch<AdminUserListResponse>(`/api/v1/admin/users${qs ? `?${qs}` : ""}`);
  },

  getUser: (id: string) =>
    apiFetch<AgencyDetail>(`/api/v1/admin/users/${id}`),

  updateUser: (id: string, data: UpdateUserRequest) =>
    apiFetch<AdminUserListItem>(`/api/v1/admin/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  resetPassword: (id: string, new_password: string) =>
    apiFetch<{ success: boolean }>(`/api/v1/admin/users/${id}/reset-password`, {
      method: "POST",
      body: JSON.stringify({ new_password }),
    }),

  deleteUser: async (id: string): Promise<void> => {
    const cookieStore = await cookies();
    const session = cookieStore.get("zentro_session")?.value;
    const res = await fetch(`${BASE}/api/v1/admin/users/${id}`, {
      method: "DELETE",
      headers: session ? { Cookie: `zentro_session=${session}` } : {},
      cache: "no-store",
    });
    if (!res.ok && res.status !== 204) {
      const parsed = await readJsonBody<{ detail?: string }>(res);
      if (parsed.ok) {
        const detail = detailFromUnknownJson(parsed.data);
        throw new Error(detail || `Delete failed ${res.status}`);
      }
      throw new Error(parsed.bodyPreview || `Delete failed ${res.status}`);
    }
  },

  getLeadQuality: () =>
    apiFetch<QualityReport>("/api/v1/admin/leads/quality-report"),

  getSystemHealth: () =>
    apiFetch<SystemHealth>("/api/v1/admin/system/health"),

  runNormalization: () =>
    apiFetch<{ status: string; triggered_by: string }>(
      "/api/v1/admin/system/run-normalization",
      { method: "POST" }
    ),

  retrainModels: () =>
    apiFetch<{ status: string; triggered_by: string }>(
      "/api/v1/admin/system/retrain-models",
      { method: "POST" }
    ),
};
