"use client";

import { Moon, Sun } from "lucide-react";

import { cn } from "@/lib/cn";
import { useTheme } from "@/app/providers/theme-provider";

/**
 * Sun / moon control with smooth icon swap; theme persists via ThemeProvider.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggleTheme, mounted } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      className={cn(
        "relative inline-flex h-10 w-10 items-center justify-center rounded-xl",
        "border border-[color:var(--border-color)] bg-[color:var(--card-bg)] backdrop-blur-md",
        "text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)]",
        "hover:shadow-[0_0_24px_rgba(99,102,241,0.2)] transition-all duration-300",
        "btn-ripple",
        className
      )}
    >
      {!mounted ? (
        <Sun className="h-4 w-4 opacity-40" />
      ) : theme === "dark" ? (
        <Moon className="h-4 w-4 transition-transform duration-300" />
      ) : (
        <Sun className="h-4 w-4 text-amber-500 transition-transform duration-300" />
      )}
    </button>
  );
}
