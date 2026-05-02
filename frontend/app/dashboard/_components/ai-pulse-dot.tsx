"use client";

import { cn } from "@/lib/cn";

/**
 * Subtle “AI is working” indicator with tooltip (title attribute).
 */
export function AiPulseDot({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "relative inline-flex h-2.5 w-2.5 rounded-full",
        "bg-gradient-to-br from-primary to-accent ai-pulse-dot",
        "ring-2 ring-[color:var(--card-bg-solid)] dark:ring-[color:var(--bg-primary)]",
        className
      )}
      title="AI is analyzing your leads"
      aria-label="AI is analyzing your leads"
    />
  );
}
