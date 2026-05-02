"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import {
  Flame,
  Briefcase,
  Building2,
  Clock,
  AlertCircle,
  Loader2,
  ExternalLink,
} from "lucide-react";

interface AutoSignal {
  id: string;
  company_name: string;
  signal_source: string;
  signal_type: string;
  signal_detail?: string;
  why_now?: string;
  insurance_need?: string;
  recommended_product?: string;
  source_url?: string;
  confidence?: number;
  detected_at: string;
  lead_id?: string;
  company_id?: string;
}

const SOURCE_CONFIG: Record<string, { icon: React.ElementType; label: string; color: string; bg: string }> = {
  tender_monitor: {
    icon: Flame,
    label: "Tender",
    color: "#ef4444",
    bg: "rgba(239,68,68,0.1)",
  },
  job_board_monitor: {
    icon: Briefcase,
    label: "Hiring",
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.1)",
  },
  ssm_monitor: {
    icon: Building2,
    label: "New",
    color: "#3b82f6",
    bg: "rgba(59,130,246,0.1)",
  },
  renewal_monitor: {
    icon: Clock,
    label: "Renewal",
    color: "#a855f7",
    bg: "rgba(168,85,247,0.1)",
  },
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function LiveSignalFeed() {
  const [signals, setSignals] = useState<AutoSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSignals() {
      try {
        const res = await fetch("/api/v1/jobs/signals/recent?limit=20", {
          credentials: "include",
        });
        if (!res.ok) throw new Error("Failed to load signals");
        const data = await res.json();
        setSignals(Array.isArray(data) ? data : []);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error");
      } finally {
        setLoading(false);
      }
    }
    fetchSignals();
  }, []);

  if (loading) {
    return (
      <Card className="card-hover">
        <CardContent className="p-6">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" style={{ color: "var(--text-tertiary)" }} />
            <span className="text-sm" style={{ color: "var(--text-tertiary)" }}>Loading signals...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="card-hover">
        <CardContent className="p-6">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4" style={{ color: "var(--color-error)" }} />
            <span className="text-sm" style={{ color: "var(--color-error)" }}>{error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (signals.length === 0) {
    return (
      <Card className="card-hover">
        <CardContent className="p-6">
          <h3 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>Live Signal Feed</h3>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-tertiary)" }}>
            Auto-detected insurance buying signals
          </p>
          <div className="mt-4 text-center py-6">
            <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full" style={{ backgroundColor: "var(--bg-tertiary)" }}>
              <Building2 className="h-5 w-5" style={{ color: "var(--text-tertiary)" }} />
            </div>
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>No signals yet</p>
            <p className="text-xs mt-1" style={{ color: "var(--text-tertiary)" }}>
              Monitors run every 6 hours — check back soon
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="card-hover">
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>Live Signal Feed</h3>
            <p className="text-xs mt-0.5" style={{ color: "var(--text-tertiary)" }}>
              Auto-detected insurance buying signals
            </p>
          </div>
          <div className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ backgroundColor: "var(--color-brand)" }} />
            <span className="relative inline-flex rounded-full h-2 w-2" style={{ backgroundColor: "var(--color-brand)" }} />
          </div>
        </div>

        <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
          {signals.map((sig) => {
            const config = SOURCE_CONFIG[sig.signal_source] || SOURCE_CONFIG.ssm_monitor;
            const Icon = config.icon;
            const href = sig.lead_id
              ? `/dashboard/leads?id=${sig.lead_id}`
              : sig.company_id
              ? `/dashboard/leads?search=${encodeURIComponent(sig.company_name)}`
              : "#";

            return (
              <div
                key={sig.id}
                className="group rounded-lg p-3 transition-colors hover:opacity-90"
                style={{ backgroundColor: "var(--bg-tertiary)" }}
              >
                <div className="flex items-start gap-3">
                  <div
                    className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg"
                    style={{ backgroundColor: config.bg }}
                  >
                    <Icon className="h-4 w-4" style={{ color: config.color }} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: config.color }}>
                        {config.label}
                      </span>
                      <span className="text-[11px] flex-shrink-0" style={{ color: "var(--text-tertiary)" }}>
                        {timeAgo(sig.detected_at)}
                      </span>
                    </div>
                    <p className="mt-0.5 text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
                      {sig.company_name}
                    </p>
                    <p className="mt-0.5 text-xs line-clamp-2" style={{ color: "var(--text-secondary)" }}>
                      {sig.why_now || sig.signal_detail || sig.insurance_need}
                    </p>
                    {sig.recommended_product && (
                      <p className="mt-1 text-[11px] font-medium" style={{ color: "var(--color-brand)" }}>
                        → {sig.recommended_product}
                      </p>
                    )}
                    {sig.lead_id && (
                      <Link href={href} className="mt-2 inline-flex items-center gap-1 text-xs font-medium hover:underline" style={{ color: "var(--color-brand)" }}>
                        View Lead <ExternalLink className="h-3 w-3" />
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
