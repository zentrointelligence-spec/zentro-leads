"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, Flame, Zap, TrendingUp, Snowflake, ArrowRight, MessageSquare, Mail,
  Phone, MapPin, Globe, Clock, CheckCircle2,
  Send, ChevronDown, Loader2, Link2, Calendar, Copy
} from "lucide-react";
import { toast } from "sonner";

import type { Lead } from "@/lib/api";
import { emailFromLead, companyNameFromLead } from "@/lib/lead-view";
import { patchLeadStatus, sendOutreach } from "@/lib/leads-client";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";
import { Dialog, DialogHeader, DialogTitle, DialogBody, DialogFooter } from "@/components/ui/dialog";
import { syncLeadToZims, suppressLead } from "../actions";

const STATUS_OPTIONS = [
  { value: "new", label: "New", color: "#3b82f6" },
  { value: "contacted", label: "Contacted", color: "#f59e0b" },
  { value: "replied", label: "Replied", color: "#eab308" },
  { value: "meeting", label: "Meeting", color: "#a855f7" },
  { value: "closed", label: "Closed", color: "#10b981" },
  { value: "lost", label: "Lost", color: "#6b7280" },
];

const TIER_META: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  hot: { icon: Flame, color: "#ef4444", label: "HOT" },
  warm: { icon: Zap, color: "#f59e0b", label: "WARM" },
  potential: { icon: TrendingUp, color: "#f59e0b", label: "POTENTIAL" },
  cold: { icon: Snowflake, color: "#6b7280", label: "COLD" },
};

function Section({ title, icon: Icon, children }: { title: string; icon: React.ElementType; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4" style={{ color: "var(--color-brand)" }} />
        <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>{title}</h4>
      </div>
      {children}
    </div>
  );
}

function SignalPill({ label, icon: Icon, color }: { label: string; icon: React.ElementType; color: string }) {
  return (
    <div className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium" style={{ backgroundColor: "var(--bg-tertiary)", color }}>
      <Icon className="h-3 w-3" />
      {label}
    </div>
  );
}

function InfoRow({ label, value, icon: Icon }: { label: string; value: React.ReactNode; icon?: React.ElementType }) {
  if (!value || value === "—" || value === "" || value === null || value === undefined) return null;
  return (
    <div className="flex items-start gap-2.5">
      {Icon ? <Icon className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" style={{ color: "var(--text-tertiary)" }} /> : null}
      <div className="min-w-0">
        <p className="text-[11px] font-medium uppercase tracking-wide" style={{ color: "var(--text-tertiary)" }}>{label}</p>
        <p className="text-sm font-medium mt-0.5" style={{ color: "var(--text-secondary)" }}>{value}</p>
      </div>
    </div>
  );
}

function WhyNowSection({ lead }: { lead: Lead }) {
  const signals = lead.intent_signals ?? [];
  const whyNow = lead.icp_reason || "";

  return (
    <div className="rounded-xl p-4 space-y-3" style={{ backgroundColor: "var(--bg-tertiary)", border: "1px solid var(--border-primary)" }}>
      <div className="flex items-center gap-2">
        <TrendingUp className="h-4 w-4" style={{ color: "var(--color-brand)" }} />
        <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>Why Now</h4>
      </div>

      {whyNow ? (
        <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{whyNow}</p>
      ) : null}

      {signals.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {signals.includes("hiring") && <SignalPill label="Hiring" icon={TrendingUp} color="#10b981" />}
          {signals.includes("funding") && <SignalPill label="Funding" icon={TrendingUp} color="#3b82f6" />}
          {signals.includes("expansion") && <SignalPill label="Expansion" icon={TrendingUp} color="#a855f7" />}
          {signals.includes("new_product") && <SignalPill label="New Product" icon={TrendingUp} color="#f59e0b" />}
          {signals.includes("job_posting") && <SignalPill label="Job Posting" icon={TrendingUp} color="#ec4899" />}
          {signals.includes("recent_news") && <SignalPill label="Recent News" icon={TrendingUp} color="#06b6d4" />}
          {signals.filter((s) => !["hiring", "funding", "expansion", "new_product", "job_posting", "recent_news"].includes(s)).map((s: string, idx: number) => (
            <SignalPill key={`signal-${idx}`} label={s} icon={TrendingUp} color="var(--text-tertiary)" />
          ))}
        </div>
      )}

      {!whyNow && signals.length === 0 && (
        <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>No signals detected yet</p>
      )}
    </div>
  );
}

function AIOutreachSection({ lead }: { lead: Lead }) {
  const [tab, setTab] = useState<"whatsapp" | "email">("whatsapp");
  const [msg, setMsg] = useState("");
  const [sending, setSending] = useState(false);

  const email = emailFromLead(lead);
  const phone = lead.person?.phone;

  const handleSend = async () => {
    if (!msg.trim()) return;
    setSending(true);
    try {
      await sendOutreach(lead.id, tab);
      setMsg("");
      toast.success(`${tab === "whatsapp" ? "WhatsApp" : "Email"} outreach sent`);
      if (tab === "whatsapp" && phone) {
        const clean = phone.replace(/\D/g, "");
        window.open(`https://wa.me/${clean}`, "_blank", "noopener,noreferrer");
      } else if (tab === "email" && email) {
        window.open(
          `mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent("Hello from LeadRadar")}&body=${encodeURIComponent(msg)}`,
          "_blank"
        );
      }
    } catch {
      toast.error(`Failed to send ${tab === "whatsapp" ? "WhatsApp" : "email"} outreach`);
    } finally {
      setSending(false);
    }
  };

  const disabled = tab === "whatsapp" ? !phone : !email;

  return (
    <div className="rounded-xl p-4 space-y-3" style={{ backgroundColor: "var(--bg-tertiary)", border: "1px solid var(--border-primary)" }}>
      <div className="flex items-center gap-2">
        <MessageSquare className="h-4 w-4" style={{ color: "var(--color-brand)" }} />
        <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>AI Outreach</h4>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => setTab("whatsapp")}
          className={cn("flex-1 rounded-lg px-3 py-2 text-xs font-medium transition-all", tab === "whatsapp" ? "font-semibold" : "")}
          style={tab === "whatsapp" ? { backgroundColor: "var(--bg-card)", color: "var(--text-primary)", border: "1px solid var(--border-primary)" } : { color: "var(--text-tertiary)" }}
        >
          WhatsApp
        </button>
        <button
          onClick={() => setTab("email")}
          className={cn("flex-1 rounded-lg px-3 py-2 text-xs font-medium transition-all", tab === "email" ? "font-semibold" : "")}
          style={tab === "email" ? { backgroundColor: "var(--bg-card)", color: "var(--text-primary)", border: "1px solid var(--border-primary)" } : { color: "var(--text-tertiary)" }}
        >
          Email
        </button>
      </div>

      {disabled && (
        <div className="rounded-lg px-3 py-2 text-xs" style={{ backgroundColor: "var(--bg-card)", color: "var(--text-tertiary)", border: "1px solid var(--border-primary)" }}>
          No {tab === "whatsapp" ? "phone" : "email"} on file
        </div>
      )}

      <textarea
        value={msg}
        onChange={(e) => setMsg(e.target.value)}
        placeholder={tab === "whatsapp" ? "Type your WhatsApp message..." : "Type your email..."}
        disabled={disabled || sending}
        className="w-full rounded-lg px-3 py-2.5 text-sm min-h-[100px] resize-y outline-none transition-all focus:ring-2"
        style={{
          backgroundColor: "var(--bg-card)",
          border: "1px solid var(--border-primary)",
          color: "var(--text-primary)",
        }}
      />

      <div className="flex items-center justify-between">
        <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
          {tab === "whatsapp" ? (phone ?? "No phone") : (email ?? "No email")}
        </span>
        <Button size="sm" onClick={handleSend} disabled={disabled || !msg.trim() || sending} leftIcon={sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}>
          Send
        </Button>
      </div>
    </div>
  );
}

function ScoreBreakdownSection({ lead }: { lead: Lead }) {
  const bars = (lead.score_breakdown ?? {}) as Record<string, number>;
  const total = lead.lead_score ?? 0;

  return (
    <Section title="Score Breakdown" icon={TrendingUp}>
      <div className="space-y-2">
        {Object.entries(bars).map(([label, value]) => (
          <div key={label}>
            <div className="flex items-center justify-between text-[11px] mb-1">
              <span className="capitalize font-medium" style={{ color: "var(--text-secondary)" }}>{label.replace(/_/g, " ")}</span>
              <span className="font-bold tabular-nums" style={{ color: "var(--text-primary)" }}>{value}</span>
            </div>
            <div className="h-1.5 w-full rounded-full overflow-hidden" style={{ backgroundColor: "var(--bg-tertiary)" }}>
              <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(100, value * 10)}%`, backgroundColor: "var(--color-brand)" }} />
            </div>
          </div>
        ))}
        {Object.keys(bars).length === 0 && (
          <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>No breakdown available</p>
        )}
      </div>
      <div className="flex items-center justify-between pt-2 border-t" style={{ borderColor: "var(--border-primary)" }}>
        <span className="text-xs font-medium" style={{ color: "var(--text-tertiary)" }}>Total Score</span>
        <span className="text-lg font-extrabold" style={{ color: "var(--color-brand)" }}>{total}</span>
      </div>
    </Section>
  );
}

function ActivityTimeline({ lead }: { lead: Lead }) {
  const noteText = lead.notes;
  const items = noteText ? noteText.split("\n").filter((n) => n.trim()) : [];

  return (
    <Section title="Activity" icon={Clock}>
      <div className="space-y-3">
        {items.length > 0 ? items.map((note, i) => (
          <div key={i} className="flex gap-3">
            <div className="relative flex flex-col items-center">
              <div className="h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: "var(--color-brand)" }} />
              {i < items.length - 1 && <div className="w-px flex-1 mt-1" style={{ backgroundColor: "var(--border-primary)" }} />}
            </div>
            <div className="pb-3 min-w-0">
              <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{note}</p>
              <p className="text-[10px] mt-0.5" style={{ color: "var(--text-tertiary)" }}>{new Date(lead.created_at).toLocaleDateString()}</p>
            </div>
          </div>
        )) : (
          <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>No activity yet</p>
        )}
      </div>
    </Section>
  );
}

function ICPValidation({ lead }: { lead: Lead }) {
  const icp = lead.icp_match_score ?? 0;
  const match = icp >= 70 ? "Strong" : icp >= 40 ? "Fair" : "Weak";
  const color = icp >= 70 ? "#10b981" : icp >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <Section title="ICP Validation" icon={CheckCircle2}>
      <div className="rounded-xl p-4 space-y-3" style={{ backgroundColor: "var(--bg-tertiary)", border: "1px solid var(--border-primary)" }}>
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{match} Match</span>
          <span className="text-lg font-extrabold" style={{ color }}>{icp}%</span>
        </div>
        <div className="h-2 w-full rounded-full overflow-hidden" style={{ backgroundColor: "var(--bg-card)" }}>
          <div className="h-full rounded-full transition-all" style={{ width: `${icp}%`, backgroundColor: color }} />
        </div>
        <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          {lead.icp_verdict || "This lead matches your ICP based on industry, company size, and geographic criteria."}
        </p>
        {lead.recommended_product && (
          <div className="rounded-lg px-3 py-2 text-xs font-medium" style={{ backgroundColor: "var(--bg-card)", color: "var(--color-brand)", border: "1px solid var(--color-brand-border)" }}>
            Recommended: {lead.recommended_product}
          </div>
        )}
      </div>
    </Section>
  );
}

export function LeadDrawer({
  lead,
  onClose,
  onLeadUpdated,
  onLeadSuppressed,
}: {
  lead: Lead | null;
  onClose: () => void;
  onLeadUpdated: (l: Lead) => void;
  onLeadSuppressed: (id: string) => void;
}) {
  const [statusOpen, setStatusOpen] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [showSuppress, setShowSuppress] = useState(false);
  const [showZims, setShowZims] = useState(false);
  const [zimsLoading, setZimsLoading] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) onClose();
    }
    if (lead) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [lead, onClose]);

  useEffect(() => {
    function handleEsc(e: KeyboardEvent) { if (e.key === "Escape") onClose(); }
    if (lead) document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [lead, onClose]);

  const handleStatusChange = useCallback(
    async (newStatus: string) => {
      if (!lead || statusLoading) return;
      setStatusLoading(true);
      try {
        const updated = await patchLeadStatus(lead.id, newStatus as Lead["status"]);
        onLeadUpdated(updated);
        toast.success(`Status changed to ${newStatus}`);
      } catch {
        toast.error("Failed to update status");
      } finally {
        setStatusLoading(false);
        setStatusOpen(false);
      }
    },
    [lead, statusLoading, onLeadUpdated]
  );

  const handleSuppress = useCallback(async () => {
    if (!lead) return;
    try {
      await suppressLead(lead.id);
      onLeadSuppressed(lead.id);
      setShowSuppress(false);
      onClose();
    } catch {
      toast.error("Failed to suppress lead");
    }
  }, [lead, onLeadSuppressed, onClose]);

  const handlePushToZims = useCallback(async () => {
    if (!lead) return;
    setZimsLoading(true);
    try {
      await syncLeadToZims(lead.id);
      toast.success("Pushed to ZIMS successfully");
      setShowZims(false);
    } catch {
      toast.error("Failed to push to ZIMS");
    } finally {
      setZimsLoading(false);
    }
  }, [lead]);

  if (!lead) return null;

  const name = companyNameFromLead(lead);
  const email = emailFromLead(lead);
  const tier = lead.lead_tier || "potential";
  const tierMeta = TIER_META[tier] || TIER_META.potential;
  const TierIcon = tierMeta.icon;
  const currentStatus = STATUS_OPTIONS.find((s) => s.value === lead.status) || STATUS_OPTIONS[0];

  return (
    <>
      <AnimatePresence>
        {lead && (
          <motion.div
            key={`drawer-${lead.id}`}
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 260 }}
            className="fixed inset-y-0 right-0 z-50 w-full sm:w-[480px] shadow-2xl overflow-y-auto"
            style={{ backgroundColor: "var(--bg-primary)" }}
            ref={drawerRef}
          >
            {/* Header */}
            <div className="sticky top-0 z-10 px-5 pt-5 pb-4 space-y-4" style={{ backgroundColor: "var(--bg-primary)" }}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl text-sm font-extrabold"
                    style={{ backgroundColor: "var(--bg-tertiary)", color: "var(--text-primary)" }}
                  >
                    {name ? name.slice(0, 2).toUpperCase() : "?"}
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-base font-bold truncate" style={{ color: "var(--text-primary)" }}>{name}</h3>
                    <div className="flex items-center gap-2 mt-0.5">
                      <div className="flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ backgroundColor: tierMeta.color + "18", color: tierMeta.color }}>
                        <TierIcon className="h-3 w-3" />
                        {tierMeta.label}
                      </div>
                      <span className="text-xs font-bold tabular-nums" style={{ color: "var(--text-tertiary)" }}>Score {lead.lead_score ?? 0}</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors"
                  style={{ backgroundColor: "var(--bg-tertiary)", color: "var(--text-tertiary)" }}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Status */}
              <div className="relative">
                <button
                  onClick={() => setStatusOpen((v) => !v)}
                  disabled={statusLoading}
                  className="flex w-full items-center justify-between rounded-lg px-3.5 py-2.5 text-sm font-medium transition-colors"
                  style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)", color: "var(--text-primary)" }}
                >
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: currentStatus.color }} />
                    {currentStatus.label}
                  </span>
                  <ChevronDown className={cn("h-4 w-4 transition-transform", statusOpen ? "rotate-180" : "")} style={{ color: "var(--text-tertiary)" }} />
                </button>
                {statusOpen && (
                  <div className="absolute left-0 right-0 top-full z-20 mt-1.5 rounded-xl p-1.5 shadow-lg" style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-primary)" }}>
                    {STATUS_OPTIONS.map((s) => (
                      <button
                        key={s.value}
                        onClick={() => handleStatusChange(s.value)}
                        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-hover"
                        style={{ color: "var(--text-secondary)" }}
                      >
                        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} />
                        {s.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Quick Actions */}
              <div className="flex gap-2">
                {tier === "hot" && (
                  <Button size="sm" variant="outline" className="flex-1" onClick={() => setShowZims(true)}>
                    Push to ZIMS
                  </Button>
                )}
                <Button size="sm" variant="outline" className="flex-1" onClick={() => setShowSuppress(true)}>
                  Suppress
                </Button>
              </div>
            </div>

            {/* Body */}
            <div className="px-5 pb-8 space-y-6">
              {/* Why Now */}
              <WhyNowSection lead={lead} />

              {/* AI Outreach */}
              <AIOutreachSection lead={lead} />

              {/* Score Breakdown */}
              <ScoreBreakdownSection lead={lead} />

              {/* Company Info */}
              <Section title="Company Info" icon={MapPin}>
                <div className="grid grid-cols-1 gap-3">
                  <InfoRow label="Industry" value={lead.company?.industry} icon={Globe} />
                  <InfoRow label="Size" value={lead.company?.employee_range} icon={TrendingUp} />
                  <InfoRow label="Location" value={lead.company?.city ? `${lead.company.city}${lead.company.country ? `, ${lead.company.country}` : ""}` : null} icon={MapPin} />
                  <InfoRow label="Website" value={lead.company?.website ? <a href={lead.company.website} target="_blank" rel="noreferrer" className="underline-offset-2 hover:underline" style={{ color: "var(--color-brand)" }}>{lead.company.website}</a> : null} icon={Link2} />
                  <InfoRow label="LinkedIn" value={lead.company?.linkedin_url ? <a href={lead.company.linkedin_url} target="_blank" rel="noreferrer" className="underline-offset-2 hover:underline" style={{ color: "var(--color-brand)" }}>Company Profile</a> : null} icon={Link2} />
                  <InfoRow label="Years in Business" value={lead.company?.years_in_business} icon={Calendar} />
                  <InfoRow label="Revenue Estimate" value={lead.company?.revenue_estimate} icon={TrendingUp} />
                  <InfoRow label="Decision Maker" value={lead.company?.decision_maker_name ? `${lead.company.decision_maker_name}${lead.company.decision_maker_title ? ` — ${lead.company.decision_maker_title}` : ""}` : null} icon={Phone} />
                  <InfoRow label="SSM Verified" value={lead.company?.ssm_verified ? "Yes" : undefined} icon={CheckCircle2} />
                </div>
              </Section>

              {/* Contact */}
              <Section title="Contact Details" icon={Mail}>
                <div className="grid grid-cols-1 gap-3">
                  <InfoRow label="Name" value={lead.person?.full_name} icon={Phone} />
                  <InfoRow label="Title" value={lead.person?.job_title} icon={TrendingUp} />
                  <InfoRow label="Email" value={email ? (
                    <button
                      onClick={() => { navigator.clipboard.writeText(email); toast.success("Copied"); }}
                      className="inline-flex items-center gap-1.5 underline-offset-2 hover:underline"
                      style={{ color: "var(--color-brand)" }}
                    >
                      {email} <Copy className="h-3 w-3" />
                    </button>
                  ) : null} icon={Mail} />
                  <InfoRow label="Phone" value={lead.person?.phone} icon={Phone} />
                  <InfoRow label="WhatsApp" value={lead.person?.whatsapp} icon={Phone} />
                  <InfoRow label="LinkedIn" value={lead.person?.linkedin_url ? <a href={lead.person.linkedin_url} target="_blank" rel="noreferrer" className="underline-offset-2 hover:underline" style={{ color: "var(--color-brand)" }}>Profile</a> : null} icon={Link2} />
                </div>
              </Section>

              {/* ICP */}
              <ICPValidation lead={lead} />

              {/* Activity */}
              <ActivityTimeline lead={lead} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Suppress Dialog */}
      <Dialog open={showSuppress} onClose={() => setShowSuppress(false)}>
        <DialogHeader onClose={() => setShowSuppress(false)}>
          <DialogTitle>Suppress this lead?</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>This will permanently remove {name} from your pipeline.</p>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowSuppress(false)}>Cancel</Button>
          <Button variant="danger" onClick={handleSuppress}>Suppress</Button>
        </DialogFooter>
      </Dialog>

      {/* ZIMS Dialog */}
      <Dialog open={showZims} onClose={() => setShowZims(false)}>
        <DialogHeader onClose={() => setShowZims(false)}>
          <DialogTitle>Push to ZIMS</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>Sync {name} to your ZIMS CRM?</p>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowZims(false)}>Cancel</Button>
          <Button onClick={handlePushToZims} disabled={zimsLoading} leftIcon={zimsLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}>
            Push
          </Button>
        </DialogFooter>
      </Dialog>
    </>
  );
}
