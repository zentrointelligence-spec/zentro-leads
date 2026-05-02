"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
}

function Toggle({
  checked,
  onChange,
  label,
  description,
  disabled,
}: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className="flex items-center justify-between w-full text-left disabled:opacity-50"
    >
      <div className="flex-1">
        {label && (
          <span className="block text-sm font-medium text-foreground-primary">
            {label}
          </span>
        )}
        {description && (
          <span className="block text-xs text-foreground-muted mt-0.5">
            {description}
          </span>
        )}
      </div>
      <div
        className={cn(
          "relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-fast focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2",
          checked ? "bg-primary" : "bg-background-secondary border-border",
          disabled && "cursor-not-allowed"
        )}
      >
        <span
          className={cn(
            "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-fast",
            checked ? "translate-x-5" : "translate-x-0"
          )}
        />
      </div>
    </button>
  );
}

export { Toggle };
