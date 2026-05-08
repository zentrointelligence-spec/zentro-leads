"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft, Flame, Zap, TrendingUp, Snowflake,
  CheckCircle2, XCircle, Loader2, Sparkles, MessageSquare,
  AlertTriangle, RefreshCcw,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/cn";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ScoreFactor {
  name:            string;
  points_awarded:  number;
  points_possible: number;
  met:             boolean;
  reason:          string;
}

interface ICPMatch {
  industry:          boolean;
  location:          boolean;
  company_size:      boolean;
  role:              boolean;
  overall_match_pct: number;
}

interface ScoreBreakdown {
  total_score:    number;
  tier:           string;
  factors:        ScoreFactor[];
  ai_explanation: string;
  signals:        string[];
  icp_match:      ICPMatch;
}

// ── Tier config ────────────────────────────────────────────────────────────────

const TIER_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  HOT:       { icon: Flame,      color: "#ef4444", bg: "rgba(239,68,68,0.12)",   label: "HOT"       },
  WARM:      { icon: Zap,        color: "#f59e0b", bg: "rgba(245,158,11,0.12)",  label: "WARM"      },
  POTENTIAL: { icon: TrendingUp, color: "#3b82f6", bg: "rgba(59,130,246,0.12)",  label: "POTENTIAL" },
  COLD:      { icon: Snowflake,  color: "#6b7280", bg: "rgba(107,114,128,0.12)", label: "COLD"      },
};

function getTier(tier: string) {
  return TIER_CONFIG[tier.toUpperCase()] ?? TIER_CONFIG.POTENTIAL;
}

// ── Score circle ───────────────────────────────────────────────────────────────

function ScoreCircle({ score, tier }: { score: number; tier: string }) {
  const cfg   = getTier(tier);
  const TierIcon = cfg.icon;
  const radius = 54;
  const circ   = 2 * Math.PI * radius;
  const offset = circ - (score / 100) * circ;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative h-36 w-36">
        <svg className="h-full w-full -rotate-90" viewBox="0 0 128 128">
          <circle cx="64" cy="64" r={radius} fill="none" strokeWidth="10" stroke="var(--bg-tertiary)" />
          <circle
            cx="64" cy="64" r={radius}
            fill="none" strokeWidth="10"
            stroke={cfg.color}
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 1s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-black tabular-nums" style={{ color: cfg.color }}>{score}</span>
          <span className="text-[11px] font-bold uppercase tracking-widest" style={{ color: "var(--text-tertiary)" }}>/ 100</span>
        </div>
      </div>
      <div className="flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-bold" style={{ backgroundColor: cfg.bg, color: cfg.color }}>
        <TierIcon className="h-4 w-4" />
        {cfg.label}
      </div>
    </div>
  );
}

// ── Score factor row ───────────────────────────────────────────────────────────

function FactorRow({ factor }: { factor: ScoreFactor }) {
  const pct = factor.points_possible > 0
    ? (factor.points_awarded / factor.points_possible) * 100
    : 0;
  const barColor = pct >= 80 ? "#10b981" : pct >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <div className="rounded-xl p-4 space-y-2.5" style={{ backgroundColor: "var(--bg-tertiary)", border: "1px solid var(--border-primary)" }}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          {factor.met
            ? <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-emerald-400" />
            : <XCircle      className="h-4 w-4 flex-shrink-0 text-red-400" />
          }
          <span className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>{factor.name}</span>
        </div>
        <span className="text-sm font-black tabular-nums flex-shrink-0" style={{ color: factor.met ? "#10b981" : "var(--text-tertiary)" }}>
          {factor.points_awarded}<span className="text-xs font-medium" style={{ color: "var(--text-tertiary)" }}>/{factor.points_possible}</span>
        </span>
      </div>

      <div className="h-1.5 w-full rounded-full overflow-hidden" style={{ backgroundColor: "var(--bg-card)" }}>
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: barColor }}
        />
      </div>

      <p className="text-xs leading-relaxed" style={{ color: "var(--text-tertiary)" }}>{factor.reason}</p>
    </div>
  );
}

// ── ICP match grid ─────────────────────────────────────────────────────────────

function ICPMatchGrid({ icp }: { icp: ICPMatch }) {
  const dims: { label: string; met: boolean }[] = [
    { label: "Industry",     met: icp.industry    },
    { label: "Location",     met: icp.location     },
    { label: "Company Size", met: icp.company_size },
    { label: "Role",         met: icp.role         },
  ];

  const pctColor = icp.overall_match_pct >= 70 ? "#10b981" : icp.overall_match_pct >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>Overall ICP Match</span>
        <span className="text-xl font-black tabular-nums" style={{ color: pctColor }}>{icp.overall_match_pct}%</span>
      </div>
      <div className="h-2 w-full rounded-full overflow-hidden" style={{ backgroundColor: "var(--bg-tertiary)" }}>
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${icp.overall_match_pct}%`, backgroundColor: pctColor }} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        {dims.map(({ label, met }) => (
          <div key={label} className="flex items-center gap-2 rounded-lg px-3 py-2.5" style={{ backgroundColor: "var(--bg-tertiary)", border: `1px solid ${met ? "rgba(16,185,129,0.2)" : "var(--border-primary)"}` }}>
            {met
              ? <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0 text-emerald-400" />
              : <XCircle      className="h-3.5 w-3.5 flex-shrink-0 text-red-400" />
            }
            <span className="text-xs font-medium" style={{ color: met ? "var(--text-primary)" : "var(--text-tertiary)" }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Intent signals ─────────────────────────────────────────────────────────────

const SIGNAL_COLORS: Record<string, string> = {
  hiring:      "#10b981",
  funded:      "#3b82f6",
  expanding:   "#a855f7",
  job_change:  "#f59e0b",
  in_the_news: "#06b6d4",
  new_product: "#ec4899",
};

function SignalChip({ signal }: { signal: string }) {
  const color = SIGNAL_COLORS[signal.toLowerCase()] ?? "#6b7280";
  return (
    <div
      className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold capitalize"
      style={{ backgroundColor: color + "18", color, border: `1px solid ${color}30` }}
    >
      <TrendingUp className="h-3 w-3" />
      {signal.replace(/_/g, " ")}
    </div>
  );
}

// ── Outreach mini modal (inline) ───────────────────────────────────────────────

function OutreachPanel({ leadId }: { leadId: string }) {
  const [open,          setOpen]          = useState(false);
  const [channel,       setChannel]       = useState("whatsapp");
  const [language,      setLanguage]      = useState("en");
  const [insuranceType, setInsuranceType] = useState("");
  const [loading,       setLoading]       = useState(false);
  const [draft,         setDraft]         = useState<{ subject: string; body: string; follow_up: string; call_to_action: string } | null>(null);
  const [copied,        setCopied]        = useState(false);

  const generate = async () => {
    setLoading(true);
    setDraft(null);
    try {
      const res = await fetch(`/api/v1/leads/${leadId}/outreach`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ channel, language, insurance_type: insuranceType || "insurance" }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      setDraft(await res.json());
    } catch {
      toast.error("Failed to generate outreach");
    } finally {
      setLoading(false);
    }
  };

  const copy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success("Copied!");
    setTimeout(() => setCopied(false), 2000);
  };

  const displayText = draft ? (channel === "email" ? `Subject: ${draft.subject}\n\n${draft.body}` : draft.body) : "";

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition"
        style={{ backgroundColor: "var(--color-brand-bg)", color: "var(--color-brand)", border: "1px solid var(--color-brand-border)" }}
      >
        <MessageSquare className="h-4 w-4" />
        Generate Outreach
      </button>
    );
  }

  return (
    <div className="rounded-xl p-4 space-y-4" style={{ backgroundColor: "var(--bg-tertiary)", border: "1px solid var(--border-primary)" }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4" style={{ color: "var(--color-brand)" }} />
          <span className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>Generate Outreach</span>
        </div>
        <button type="button" onClick={() => setOpen(false)} className="text-xs" style={{ color: "var(--text-tertiary)" }}>✕</button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase tracking-wide" style={{ color: "var(--text-tertiary)" }}>Channel</label>
          <select value={channel} onChange={(e) => { setChannel(e.target.value); setDraft(null); }}
            className="w-full rounded-lg px-2.5 py-2 text-xs outline-none"
            style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)", color: "var(--text-primary)" }}>
            <option value="whatsapp">WhatsApp</option>
            <option value="email">Email</option>
            <option value="sms">SMS</option>
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase tracking-wide" style={{ color: "var(--text-tertiary)" }}>Language</label>
          <select value={language} onChange={(e) => { setLanguage(e.target.value); setDraft(null); }}
            className="w-full rounded-lg px-2.5 py-2 text-xs outline-none"
            style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)", color: "var(--text-primary)" }}>
            <option value="en">English</option>
            <option value="ms">Bahasa Malaysia</option>
            <option value="hi">Hindi</option>
            <option value="ta">Tamil</option>
          </select>
        </div>
      </div>

      <div className="space-y-1">
        <label className="text-[10px] font-bold uppercase tracking-wide" style={{ color: "var(--text-tertiary)" }}>Insurance Type</label>
        <input type="text" value={insuranceType} onChange={(e) => setInsuranceType(e.target.value)}
          placeholder="e.g. motor fleet, medical, fire & peril"
          className="w-full rounded-lg px-2.5 py-2 text-xs outline-none"
          style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)", color: "var(--text-primary)" }} />
      </div>

      <button type="button" onClick={generate} disabled={loading}
        className="flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-bold transition disabled:opacity-60"
        style={{ backgroundColor: "var(--color-brand)", color: "#fff" }}>
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
        {draft ? "Regenerate" : "Generate"}
      </button>

      {draft && (
        <div className="space-y-3">
          <div className="relative">
            <textarea readOnly value={displayText} rows={channel === "email" ? 7 : 4}
              className="w-full rounded-lg px-3 py-2.5 text-xs resize-none outline-none"
              style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)", color: "var(--text-primary)" }} />
            <button type="button" onClick={() => copy(displayText)}
              className="absolute right-2 top-2 rounded-md px-2 py-1 text-[10px] font-bold transition"
              style={{ backgroundColor: "var(--bg-tertiary)", color: copied ? "var(--color-brand)" : "var(--text-tertiary)" }}>
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
          {draft.follow_up && (
            <div className="rounded-lg p-3 space-y-1" style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)" }}>
              <p className="text-[10px] font-bold uppercase tracking-wide" style={{ color: "var(--text-tertiary)" }}>3-Day Follow-up</p>
              <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{draft.follow_up}</p>
              <button type="button" onClick={() => copy(draft.follow_up)}
                className="text-[10px] font-semibold" style={{ color: "var(--color-brand)" }}>Copy</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function ScoreBreakdownPage() {
  const { id: leadId } = useParams<{ id: string }>();
  const router = useRouter();

  const [data,    setData]    = useState<ScoreBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/leads/${leadId}/score-breakdown`, { credentials: "include" });
      if (res.status === 401) { router.push("/login"); return; }
      if (!res.ok) throw new Error(`${res.status}`);
      setData(await res.json());
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load";
      setError(msg);
      toast.error("Failed to load score breakdown");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [leadId]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-4 py-6">
      {/* Nav */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => router.back()}
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition hover:bg-hover"
          style={{ color: "var(--text-secondary)" }}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Lead
        </button>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition disabled:opacity-50"
          style={{ color: "var(--text-tertiary)", border: "1px solid var(--border-primary)" }}
        >
          <RefreshCcw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Loading */}
      {loading && !data && (
        <div className="flex flex-col items-center justify-center gap-3 py-20">
          <Loader2 className="h-8 w-8 animate-spin" style={{ color: "var(--color-brand)" }} />
          <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>Loading score breakdown…</p>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="flex items-center gap-3 rounded-xl p-4" style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)" }}>
          <AlertTriangle className="h-5 w-5 text-red-400" />
          <div>
            <p className="text-sm font-semibold text-red-400">Failed to load breakdown</p>
            <p className="text-xs text-red-300 mt-0.5">{error}</p>
          </div>
          <button type="button" onClick={load} className="ml-auto text-xs font-bold text-red-400 hover:text-red-300">Retry</button>
        </div>
      )}

      {data && (
        <>
          {/* Header */}
          <div className="flex flex-col items-center gap-2 rounded-2xl py-8"
            style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)" }}>
            <h1 className="text-base font-black" style={{ color: "var(--text-primary)" }}>Score Breakdown</h1>
            <ScoreCircle score={data.total_score} tier={data.tier} />
          </div>

          {/* AI Explanation */}
          {data.ai_explanation && (
            <div className="flex gap-3 rounded-xl p-4"
              style={{ backgroundColor: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.15)" }}>
              <Sparkles className="h-5 w-5 flex-shrink-0 mt-0.5 text-emerald-400" />
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-400 mb-1">AI Explanation</p>
                <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{data.ai_explanation}</p>
              </div>
            </div>
          )}

          {/* Score factors */}
          <div className="space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>Score Factors</h2>
            <div className="space-y-2">
              {data.factors.map((f) => <FactorRow key={f.name} factor={f} />)}
            </div>
          </div>

          {/* ICP match */}
          <div className="rounded-xl p-4 space-y-4" style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)" }}>
            <h2 className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>ICP Match</h2>
            <ICPMatchGrid icp={data.icp_match} />
          </div>

          {/* Intent signals */}
          {data.signals.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>
                Intent Signals <span className="normal-case font-medium">({data.signals.length} detected)</span>
              </h2>
              <div className="flex flex-wrap gap-2">
                {data.signals.map((s) => <SignalChip key={s} signal={s} />)}
              </div>
            </div>
          )}

          {/* Generate Outreach */}
          <OutreachPanel leadId={leadId} />
        </>
      )}
    </div>
  );
}
