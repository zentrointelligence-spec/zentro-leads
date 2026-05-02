"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="mb-1.5 block text-sm font-medium text-foreground-primary">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          className={cn(
            "flex w-full rounded-md border border-border bg-background-elevated px-3 py-2.5 text-sm text-foreground-primary shadow-sm transition-colors placeholder:text-foreground-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50 resize-none",
            error && "border-hot focus-visible:ring-hot/20",
            className
          )}
          {...props}
        />
        {error && <p className="mt-1 text-xs text-hot">{error}</p>}
      </div>
    );
  }
);
Textarea.displayName = "Textarea";

export { Textarea };
