"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import {
  Database,
  Layers,
  Search,
  Triangle,
  Bot,
  Clock,
  RefreshCw,
  Play,
  Cpu,
} from "lucide-react";
import type { ServiceHealth, SystemHealth } from "@/lib/api";
import { parseJsonResponse } from "@/lib/parse-json-client";

interface Props {
  initialHealth: SystemHealth | null;
}

const SERVICE_META: Record<
  keyof Omit<SystemHealth, "overall">,
  { label: string; icon: React.ElementType }
> = {
  postgresql:    { label: "PostgreSQL",    icon: Database },
  redis:         { label: "Redis",         icon: Layers },
  elasticsearch: { label: "Elasticsearch", icon: Search },
  pinecone:      { label: "Pinecone",      icon: Triangle },
  anthropic:     { label: "Anthropic AI",  icon: Bot },
  scheduler:     { label: "Scheduler",     icon: Clock },
};

const STATUS_STYLE = {
  healthy:  { border: "border-emerald-800", bg: "bg-emerald-950/30", dot: "🟢", label: "Healthy",  text: "text-emerald-400" },
  ok:       { border: "border-emerald-800", bg: "bg-emerald-950/30", dot: "🟢", label: "Healthy",  text: "text-emerald-400" },
  degraded: { border: "border-yellow-800",  bg: "bg-yellow-950/30",  dot: "🟡", label: "Degraded", text: "text-yellow-400" },
  down:     { border: "border-red-800",     bg: "bg-red-950/30",     dot: "🔴", label: "Down",     text: "text-red-400" },
};

function ServiceCard({ name, service }: { name: string; service: ServiceHealth }) {
  const meta   = SERVICE_META[name as keyof typeof SERVICE_META];
  const style  = STATUS_STYLE[service.status] ?? STATUS_STYLE.down;
  const Icon   = meta?.icon ?? Database;

  return (
    <div className={`rounded-xl border ${style.border} ${style.bg} p-5`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-gray-400" />
          <span className="text-sm font-semibold text-white">{meta?.label ?? name}</span>
        </div>
        <span className="text-base leading-none">{style.dot}</span>
      </div>
      <p className={`text-sm font-bold ${style.text}`}>{style.label.toUpperCase()}</p>
      {service.latency_ms != null && (
        <p className="text-xs text-gray-500 mt-1">Latency: {service.latency_ms}ms</p>
      )}
      {service.detail && (
        <p className="text-xs text-gray-600 mt-1 truncate" title={service.detail}>
          {service.detail}
        </p>
      )}
    </div>
  );
}

export function SystemHealthClient({ initialHealth }: Props) {
  const [health, setHealth]     = useState<SystemHealth | null>(initialHealth);
  const [loading, setLoading]   = useState(false);
  const [normBusy, setNormBusy] = useState(false);
  const [retBusy, setRetBusy]   = useState(false);
  const [confirmJob, setConfirmJob] = useState<"norm" | "retrain" | null>(null);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/system/health");
      if (res.ok) {
        const h = await parseJsonResponse<SystemHealth | null>(res, null);
        if (h && typeof h === "object" && "overall" in h) setHealth(h);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const id = setInterval(fetchHealth, 30_000);
    return () => clearInterval(id);
  }, [fetchHealth]);

  const runNormalization = async () => {
    setNormBusy(true);
    try {
      const res = await fetch("/api/admin/system/run-normalization", { method: "POST" });
      if (res.ok) {
        toast.success("Normalization job started. Check backend logs.");
      } else {
        toast.error("Failed to start normalization");
      }
    } catch {
      toast.error("Network error");
    } finally {
      setNormBusy(false);
      setConfirmJob(null);
    }
  };

  const retrainModels = async () => {
    setRetBusy(true);
    try {
      const res = await fetch("/api/admin/system/retrain-models", { method: "POST" });
      if (res.ok) {
        toast.success("Model retrain started. Will train B2B + B2C.");
      } else {
        toast.error("Failed to start retrain");
      }
    } catch {
      toast.error("Network error");
    } finally {
      setRetBusy(false);
      setConfirmJob(null);
    }
  };

  const overall = health?.overall ?? "down";
  const overallStyle = STATUS_STYLE[overall] ?? STATUS_STYLE.down;

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Confirm dialog */}
      {confirmJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="rounded-xl bg-gray-900 border border-gray-700 p-6 max-w-sm w-full mx-4">
            <h3 className="text-base font-bold text-white mb-2">
              {confirmJob === "norm" ? "Run Normalization?" : "Retrain Scoring Models?"}
            </h3>
            <p className="text-sm text-gray-400 mb-6">
              {confirmJob === "norm"
                ? "This will trigger Gemini bulk normalization for all un-normalized companies. The job runs in the background."
                : "This will retrain B2B and B2C XGBoost models using current feedback data. This may take several minutes."}
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmJob(null)}
                className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={confirmJob === "norm" ? runNormalization : retrainModels}
                className="rounded-lg bg-orange-600 hover:bg-orange-700 px-4 py-2 text-sm font-semibold text-white"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-black text-white">System Health</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-base">{overallStyle.dot}</span>
            <span className={`text-sm font-semibold ${overallStyle.text}`}>
              Overall: {overallStyle.label}
            </span>
          </div>
        </div>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg bg-gray-800 border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh now
        </button>
      </div>

      {/* Service cards */}
      {!health ? (
        <div className="flex items-center justify-center h-48">
          <p className="text-gray-500">Failed to load health data</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(Object.keys(SERVICE_META) as Array<keyof typeof SERVICE_META>).map((key) => (
            <ServiceCard key={key} name={key} service={health[key]} />
          ))}
        </div>
      )}

      <p className="text-xs text-gray-700 text-right">Auto-refreshes every 30 seconds</p>

      {/* Action buttons */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-6">
        <h2 className="text-sm font-bold text-white mb-4">Manual Jobs</h2>
        <div className="flex flex-wrap gap-4">
          <button
            onClick={() => setConfirmJob("norm")}
            disabled={normBusy}
            className="flex items-center gap-2 rounded-lg bg-indigo-700 hover:bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition-colors disabled:opacity-50"
          >
            <Play className={`h-4 w-4 ${normBusy ? "animate-pulse" : ""}`} />
            {normBusy ? "Starting…" : "Run Normalization Job"}
          </button>
          <button
            onClick={() => setConfirmJob("retrain")}
            disabled={retBusy}
            className="flex items-center gap-2 rounded-lg bg-orange-700 hover:bg-orange-600 px-5 py-3 text-sm font-semibold text-white transition-colors disabled:opacity-50"
          >
            <Cpu className={`h-4 w-4 ${retBusy ? "animate-pulse" : ""}`} />
            {retBusy ? "Starting…" : "Retrain Scoring Models"}
          </button>
        </div>
        <p className="mt-3 text-xs text-gray-600">
          Jobs run in the background. Check backend logs for progress and results.
        </p>
      </div>
    </div>
  );
}
