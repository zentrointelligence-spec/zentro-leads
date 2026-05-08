"use client";

import { useEffect } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { usePipelineStore, type PipelineLead } from "@/lib/pipeline-store";
import { Mail, Phone, Trophy, CheckCircle2, Clock, ChevronRight, RefreshCcw, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useState } from "react";

const fadeUp = { hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0 } };
const stagger = { hidden: {}, visible: { transition: { staggerChildren: 0.06 } } };

// ── Mock policy detail helpers (derived from lead ID deterministically) ────────

const FOLLOW_UP_TASKS = [
  "Send policy document",
  "Schedule renewal call",
  "Confirm beneficiary details",
  "Issue NCD letter",
];
const POLICY_TYPES = [
  "Motor Fleet", "Fire & Peril", "Liability",
  "Marine Cargo", "Medical", "Personal Accident",
];

function mockTask(lead: PipelineLead)    { return FOLLOW_UP_TASKS[lead.id.charCodeAt(lead.id.length - 1) % FOLLOW_UP_TASKS.length]; }
function mockPolicy(lead: PipelineLead)  { return POLICY_TYPES[lead.id.charCodeAt(0) % POLICY_TYPES.length]; }
function mockRenewal(lead: PipelineLead) {
  const base = new Date(lead.pushedAt);
  base.setFullYear(base.getFullYear() + 1);
  return base.toLocaleDateString("en-MY", { day: "numeric", month: "short", year: "numeric" });
}
function mockPremium(lead: PipelineLead) {
  return `RM ${((lead.id.charCodeAt(0) % 8 + 1) * 1_200).toLocaleString()}`;
}

// ── Customer card ─────────────────────────────────────────────────────────────

function CustomerCard({ lead }: { lead: PipelineLead }) {
  const [taskDone, setTaskDone] = useState(false);

  return (
    <motion.div
      variants={fadeUp}
      className="rounded-2xl border border-emerald-400/[0.12] bg-[#0d1425] p-5 transition duration-200 hover:border-emerald-400/25 hover:shadow-[0_16px_48px_rgba(16,185,129,0.08)]"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-orange-600 to-amber-500 text-sm font-black text-white">
            {lead.name.split(" ").map((p) => p[0]).join("").slice(0, 2)}
          </div>
          <div>
            <div className="text-sm font-black text-white">{lead.name}</div>
            <div className="text-xs text-slate-500">{lead.company}</div>
          </div>
        </div>
        <Trophy className="h-5 w-5 shrink-0 text-emerald-400" />
      </div>

      {/* Policy detail */}
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-white/[0.03] px-3 py-2.5">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-600">Policy Type</div>
          <div className="mt-1 text-xs font-black text-slate-200">{mockPolicy(lead)}</div>
        </div>
        <div className="rounded-xl bg-white/[0.03] px-3 py-2.5">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-600">Annual Premium</div>
          <div className="mt-1 text-xs font-black text-emerald-400">{mockPremium(lead)}</div>
        </div>
        <div className="rounded-xl bg-white/[0.03] px-3 py-2.5">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-600">Renewal Date</div>
          <div className="mt-1 flex items-center gap-1 text-xs font-semibold text-slate-300">
            <Clock className="h-3 w-3 text-amber-400" /> {mockRenewal(lead)}
          </div>
        </div>
        <div className="rounded-xl bg-white/[0.03] px-3 py-2.5">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-600">Lead Score</div>
          <div className="mt-1 text-xs font-black text-white">
            {lead.score}{" "}
            <span className={cn("text-[10px]", lead.tier === "HOT" ? "text-red-300" : "text-amber-300")}>
              {lead.tier}
            </span>
          </div>
        </div>
      </div>

      {/* Contact */}
      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
        {lead.email && <span className="flex items-center gap-1"><Mail className="h-3.5 w-3.5" /> {lead.email}</span>}
        {lead.phone && <span className="flex items-center gap-1"><Phone className="h-3.5 w-3.5" /> {lead.phone}</span>}
      </div>

      {/* Follow-up task */}
      <div className="mt-4 flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2.5">
        <div className="flex items-center gap-2">
          <CheckCircle2 className={cn("h-4 w-4 shrink-0 transition", taskDone ? "text-emerald-400" : "text-slate-600")} />
          <span className={cn("text-xs", taskDone ? "text-slate-500 line-through" : "text-slate-300")}>
            {mockTask(lead)}
          </span>
        </div>
        <button
          type="button"
          onClick={() => {
            setTaskDone(!taskDone);
            toast.success(taskDone ? "Task reopened" : "Task marked complete");
          }}
          className="flex items-center gap-1 rounded-lg bg-white/[0.05] px-2 py-1 text-[10px] font-bold text-slate-400 transition hover:bg-orange-500/15 hover:text-orange-300"
        >
          {taskDone ? "Undo" : "Done"} <ChevronRight className="h-3 w-3" />
        </button>
      </div>
    </motion.div>
  );
}

// ── Skeleton card ─────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-2xl border border-white/[0.06] bg-[#0d1425] p-5 space-y-4">
      <div className="flex items-center gap-3">
        <div className="h-11 w-11 rounded-xl bg-white/[0.06]" />
        <div className="flex-1 space-y-2">
          <div className="h-3 w-32 rounded bg-white/[0.06]" />
          <div className="h-2.5 w-20 rounded bg-white/[0.04]" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-12 rounded-xl bg-white/[0.04]" />
        ))}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CustomersPage() {
  const { leads, loading, fetchPipeline, getByStage } = usePipelineStore();

  useEffect(() => {
    fetchPipeline();
  }, [fetchPipeline]);

  const customers = getByStage("closed_won");
  const totalPremium = customers.reduce((sum, l) => sum + (l.id.charCodeAt(0) % 8 + 1) * 1_200, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-foreground-primary">Customers</h1>
          <p className="mt-1 text-sm text-foreground-muted">
            Leads marked Closed Won — with policy details and follow-up tasks.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/5 px-4 py-2 text-center">
            <div className="text-lg font-black text-emerald-400">{customers.length}</div>
            <div className="text-[10px] font-medium text-foreground-muted">Customers</div>
          </div>
          <div className="rounded-xl border border-white/[0.08] bg-card-bg px-4 py-2 text-center">
            <div className="text-lg font-black text-foreground-primary">RM {totalPremium.toLocaleString()}</div>
            <div className="text-[10px] font-medium text-foreground-muted">Est. Premium</div>
          </div>
          <button
            type="button"
            onClick={() => fetchPipeline()}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-card-bg px-3 py-2 text-xs font-semibold text-foreground-muted transition hover:bg-white/[0.06] disabled:opacity-50"
          >
            {loading
              ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
              : <RefreshCcw className="h-3.5 w-3.5" />}
            Refresh
          </button>
        </div>
      </div>

      {/* Content */}
      {loading && leads.length === 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[...Array(6)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : customers.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 py-20 text-center">
          <Trophy className="mx-auto h-12 w-12 text-slate-700" />
          <h3 className="mt-4 text-base font-black text-foreground-primary">No customers yet</h3>
          <p className="mt-2 max-w-sm text-sm text-foreground-muted">
            Move leads to the &ldquo;Closed Won&rdquo; stage in your Pipeline to see them here.
          </p>
        </div>
      ) : (
        <motion.div
          initial="hidden"
          animate="visible"
          variants={stagger}
          className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
        >
          {customers.map((lead) => (
            <CustomerCard key={lead.id} lead={lead} />
          ))}
        </motion.div>
      )}
    </div>
  );
}
