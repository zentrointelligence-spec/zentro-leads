"use client";

import { useRef, useState, useTransition } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";

import type { Lead } from "@/lib/api";

interface Props {
  onResults: (leads: Lead[]) => void;
  onClear: () => void;
}

const inputClass =
  "h-10 w-full rounded-md border border-white/[0.08] bg-[#08080a] px-3.5 text-[13px] text-zinc-100 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] placeholder:text-zinc-600 transition-[border-color,box-shadow] duration-150 ease-out hover:border-white/[0.11] focus:border-brand-blue/50 focus:outline-none focus:ring-2 focus:ring-brand-blue/20";

const THROTTLE_SAME_QUERY_MS = 480;

/**
 * Natural-language lead search — POST /api/v1/leads/search/nl via Next rewrite.
 * Throttles identical back-to-back queries to protect the API while keeping the first submit instant.
 */
export function NLSearchBar({ onResults, onClear }: Props) {
  const [q, setQ] = useState("");
  const [pending, startTransition] = useTransition();
  const lastRunRef = useRef<{ query: string; at: number }>({ query: "", at: 0 });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const query = q.trim();
    if (!query) {
      toast.error("Enter a search prompt.");
      return;
    }
    const now = Date.now();
    if (
      query === lastRunRef.current.query &&
      now - lastRunRef.current.at < THROTTLE_SAME_QUERY_MS
    ) {
      toast.message("Please wait a moment before repeating the same search.");
      return;
    }
    lastRunRef.current = { query, at: now };

    startTransition(async () => {
      try {
        const res = await fetch("/api/v1/leads/search/nl", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query }),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `Search failed (${res.status})`);
        }
        const data = (await res.json()) as Lead[];
        onResults(data);
        toast.success(`AI search: ${data.length} lead(s).`);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "AI search failed.";
        toast.error(msg);
      }
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-white/[0.06] bg-[#09090b]/60 p-1 shadow-md shadow-black/25 sm:p-1.5"
    >
      <div className="flex flex-col gap-3 p-3 sm:p-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md border border-white/[0.06] bg-white/[0.03]">
            <Sparkles className="h-3.5 w-3.5 text-brand-blue" />
          </div>
          <div>
            <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
              Natural language
            </p>
            <p className="text-[13px] font-medium tracking-tight text-zinc-200">AI search</p>
          </div>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Show me hot insurance leads hiring in KL"
            className={inputClass}
          />
          <div className="flex shrink-0 gap-2 sm:w-auto">
            <button
              type="submit"
              disabled={pending}
              className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-md bg-brand-blue px-4 text-[13px] font-medium text-white shadow-md transition-[background-color,transform,opacity] duration-150 ease-out hover:bg-brand-blue-dark active:scale-[0.98] disabled:pointer-events-none disabled:opacity-40 sm:flex-none sm:min-w-[96px]"
            >
              {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Search
            </button>
            <button
              type="button"
              onClick={() => {
                setQ("");
                onClear();
                toast.message("Cleared AI results.");
              }}
              className="inline-flex h-10 items-center justify-center rounded-md border border-white/[0.08] px-4 text-[13px] font-medium text-zinc-400 transition-colors duration-150 hover:border-white/[0.12] hover:bg-white/[0.04] hover:text-zinc-200 active:scale-[0.98]"
            >
              Clear
            </button>
          </div>
        </div>
        <p className="text-[11px] leading-snug text-zinc-600">
          Identical searches within {THROTTLE_SAME_QUERY_MS}ms are throttled to protect the API.
        </p>
      </div>
    </form>
  );
}
