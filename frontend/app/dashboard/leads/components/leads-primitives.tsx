"use client";

import { cn } from "@/lib/cn";

/**
 * Muted label for form sections and drawer fields (Stripe / Linear hierarchy).
 */
export function MutedLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500",
        className
      )}
    >
      {children}
    </span>
  );
}

interface ProgressBarProps {
  value: number;
  max: number;
  className?: string;
  barClassName?: string;
}

/**
 * Horizontal progress bar (0–100 style when max is 100).
 */
export function ProgressBar({ value, max, className, barClassName }: ProgressBarProps) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div
      className={cn(
        "h-2 w-full overflow-hidden rounded-full bg-white/[0.06] shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)]",
        className
      )}
    >
      <div
        className={cn(
          "h-full rounded-full transition-[width] duration-300 ease-out",
          barClassName ?? "bg-gradient-to-r from-brand-blue to-blue-400"
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
