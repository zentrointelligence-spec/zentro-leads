"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, icon, type, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="mb-1.5 block text-sm font-medium text-foreground-primary">
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground-muted">
              {icon}
            </div>
          )}
          <input
            type={type}
            ref={ref}
            className={cn(
              "flex w-full rounded-md border border-border bg-background-elevated px-3 py-2.5 text-sm text-foreground-primary shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-foreground-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50",
              icon && "pl-10",
              error && "border-hot focus-visible:ring-hot/20",
              className
            )}
            {...props}
          />
        </div>
        {error && <p className="mt-1 text-xs text-hot">{error}</p>}
      </div>
    );
  }
);
Input.displayName = "Input";

export { Input };
