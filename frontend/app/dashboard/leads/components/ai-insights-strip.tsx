"use client";

import { cn } from "@/lib/cn";

/**
 * Decision-first insight chips (UI placeholder copy — not wired to analytics).
 */
export function AiInsightsStrip({ className }: { className?: string }) {
  const items = [
    { emoji: "🔥", text: "3 high-priority leads detected" },
    { emoji: "⚡", text: "2 companies hiring aggressively" },
    { emoji: "💡", text: "Best time to contact: Today" },
  ];

  return (
    <div
      className={cn(
        "flex flex-wrap gap-3 rounded-2xl border border-[color:var(--border-color)]",
        "bg-[color:var(--accent-gradient-soft)] px-4 py-3 backdrop-blur-md",
        "animate-fade-up",
        className
      )}
    >
      {items.map((item) => (
        <div
          key={item.text}
          className={cn(
            "inline-flex items-center gap-2 rounded-xl border px-3 py-1.5 text-sm",
            "border-[color:var(--border-color)] bg-[color:var(--card-bg)]/80",
            "text-[color:var(--text-primary)] shadow-sm"
          )}
        >
          <span aria-hidden>{item.emoji}</span>
          <span className="text-[color:var(--text-secondary)]">{item.text}</span>
        </div>
      ))}
    </div>
  );
}
