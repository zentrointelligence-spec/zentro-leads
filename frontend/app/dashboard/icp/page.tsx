"use client";

import { useState, useTransition } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Target, Plus, Loader2, X, Sparkles, ChevronDown, ChevronUp, Zap } from "lucide-react";
import { cn } from "@/lib/cn";
import { generateLeads } from "@/app/dashboard/leads/actions";

interface ICP {
  id: string;
  name: string;
  description: string | null;
  industries: string[];
  job_titles: string[];
  seniority_levels: string[];
  company_sizes: string[];
  locations: string[];
  keywords: string[];
  intent_signals: string[];
  search_queries: string[];
  total_leads_generated: number;
  conversion_rate: number;
  is_active: boolean;
  created_at: string;
}

interface ICPListResponse {
  items: ICP[];
  total: number;
}

async function fetchICPs(): Promise<ICPListResponse> {
  const res = await fetch("/api/v1/icp/", { credentials: "include" });
  if (!res.ok) throw new Error("Failed to load ICPs");
  return res.json();
}

async function buildICPWithAI(description: string): Promise<ICP> {
  const res = await fetch("/api/v1/icp/build", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ description }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? "Failed to build ICP");
  return json;
}

function ICPCard({ icp }: { icp: ICP }) {
  const [expanded, setExpanded] = useState(false);
  const [isPending, startTransition] = useTransition();

  function handleGenerate(e: React.MouseEvent) {
    e.stopPropagation();
    startTransition(async () => {
      const result = await generateLeads(icp.id);
      if (result.ok) {
        toast.success(result.message ?? "Lead generation started — results appear shortly.");
      } else {
        toast.error(result.error ?? "Lead generation failed.");
      }
    });
  }

  return (
    <div className="bg-[#0F1B2D] border border-white/8 rounded-xl overflow-hidden">
      <div
        className="p-5 cursor-pointer hover:bg-white/2 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-6 h-6 rounded-md bg-[#3B6FFF]/15 flex items-center justify-center flex-shrink-0">
                <Target className="w-3.5 h-3.5 text-[#3B6FFF]" />
              </div>
              <h3 className="text-white font-semibold text-sm truncate">{icp.name}</h3>
            </div>
            {icp.description && (
              <p className="text-slate-400 text-xs leading-relaxed line-clamp-2 ml-8">
                {icp.description}
              </p>
            )}
            <div className="flex items-center gap-3 mt-3 ml-8">
              <span className="text-slate-500 text-xs">{icp.total_leads_generated} leads generated</span>
              <span className="text-slate-700">·</span>
              <span className="text-slate-500 text-xs">{icp.industries.length} industries</span>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={handleGenerate}
              disabled={isPending}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors",
                "bg-[#3B6FFF]/15 text-[#3B6FFF] hover:bg-[#3B6FFF]/25",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              {isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Zap className="w-3.5 h-3.5" />
              )}
              {isPending ? "Starting…" : "Generate Leads"}
            </button>
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-slate-500 mt-0.5" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-500 mt-0.5" />
            )}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-white/8 p-5 space-y-4">
          {[
            { label: "Industries", values: icp.industries, color: "bg-blue-500/10 text-blue-300" },
            { label: "Job Titles", values: icp.job_titles, color: "bg-purple-500/10 text-purple-300" },
            { label: "Seniority", values: icp.seniority_levels, color: "bg-yellow-500/10 text-yellow-300" },
            { label: "Company Sizes", values: icp.company_sizes, color: "bg-green-500/10 text-green-300" },
            { label: "Locations", values: icp.locations, color: "bg-cyan-500/10 text-cyan-300" },
            { label: "Keywords", values: icp.keywords, color: "bg-orange-500/10 text-orange-300" },
            { label: "Intent Signals", values: icp.intent_signals, color: "bg-red-500/10 text-red-300" },
          ].map(({ label, values, color }) =>
            values.length > 0 ? (
              <div key={label}>
                <p className="text-slate-400 text-xs font-medium uppercase tracking-wide mb-2">{label}</p>
                <div className="flex flex-wrap gap-1.5">
                  {values.map((v) => (
                    <span key={v} className={cn("text-xs px-2.5 py-1 rounded-full font-medium", color)}>
                      {v}
                    </span>
                  ))}
                </div>
              </div>
            ) : null
          )}
          {icp.search_queries.length > 0 && (
            <div>
              <p className="text-slate-400 text-xs font-medium uppercase tracking-wide mb-2">Search Queries</p>
              <div className="space-y-1.5">
                {icp.search_queries.map((q) => (
                  <div key={q} className="flex items-start gap-2">
                    <span className="text-[#3B6FFF] mt-0.5 flex-shrink-0">›</span>
                    <span className="text-slate-300 text-xs">{q}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ICPPage() {
  const [showModal, setShowModal] = useState(false);
  const [description, setDescription] = useState("");
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["icps"],
    queryFn: fetchICPs,
  });

  const buildMutation = useMutation({
    mutationFn: buildICPWithAI,
    onSuccess: () => {
      toast.success("ICP built successfully!");
      queryClient.invalidateQueries({ queryKey: ["icps"] });
      setShowModal(false);
      setDescription("");
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-white text-lg font-semibold">ICP Builder</h2>
          <p className="text-slate-400 text-sm mt-0.5">
            Define your Ideal Customer Profile — AI builds the full targeting criteria from one sentence.
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-[#3B6FFF] text-white text-sm font-semibold rounded-lg hover:bg-[#2855D8] transition-colors"
        >
          <Sparkles className="w-4 h-4" />
          AI Build
        </button>
      </div>

      {/* ICP List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 text-[#3B6FFF] animate-spin" />
        </div>
      ) : data?.items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-14 h-14 rounded-2xl bg-[#3B6FFF]/10 flex items-center justify-center mb-4">
            <Target className="w-7 h-7 text-[#3B6FFF]" />
          </div>
          <p className="text-white font-semibold mb-2">No ICPs yet</p>
          <p className="text-slate-400 text-sm mb-6 max-w-xs">
            Describe your business in one sentence and let AI build your complete targeting criteria.
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-[#3B6FFF] text-white text-sm font-semibold rounded-lg hover:bg-[#2855D8] transition-colors"
          >
            <Plus className="w-4 h-4" />
            Build your first ICP
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {data?.items.map((icp) => (
            <ICPCard key={icp.id} icp={icp} />
          ))}
        </div>
      )}

      {/* AI Build Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0F1B2D] border border-white/10 rounded-2xl w-full max-w-lg shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-white/8">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-[#3B6FFF]/15 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-[#3B6FFF]" />
                </div>
                <div>
                  <h3 className="text-white font-semibold">AI ICP Builder</h3>
                  <p className="text-slate-500 text-xs">Powered by Claude</p>
                </div>
              </div>
              <button
                onClick={() => { setShowModal(false); setDescription(""); }}
                className="text-slate-500 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6">
              <label className="block text-slate-300 text-sm font-medium mb-2">
                Describe what you sell (1–3 sentences)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                placeholder="e.g. I sell health insurance to SME companies in Malaysia with 10–200 employees"
                className="w-full px-3.5 py-3 rounded-lg bg-[#080f1a] border border-white/10 text-white placeholder-slate-500 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[#3B6FFF] focus:border-transparent"
              />
              <p className="text-slate-500 text-xs mt-1.5">
                Claude will generate industries, job titles, company sizes, locations, keywords, and intent signals.
              </p>
            </div>

            <div className="flex gap-3 px-6 pb-6">
              <button
                onClick={() => { setShowModal(false); setDescription(""); }}
                className="flex-1 py-2.5 rounded-lg border border-white/10 text-slate-300 text-sm font-medium hover:bg-white/5 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => buildMutation.mutate(description)}
                disabled={description.trim().length < 10 || buildMutation.isPending}
                className={cn(
                  "flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-[#3B6FFF] text-white text-sm font-semibold",
                  "hover:bg-[#2855D8] transition-colors",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
              >
                {buildMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Building…
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Build ICP with AI
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
