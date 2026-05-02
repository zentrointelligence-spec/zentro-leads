"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

const badgeVariants = {
  default: "bg-background-secondary text-foreground-secondary",
  secondary: "bg-background-secondary text-foreground-secondary border border-border",
  outline: "bg-transparent text-foreground-secondary border border-border",
  hot: "bg-hot/10 text-hot",
  warm: "bg-warm/10 text-warm",
  potential: "bg-potential/10 text-potential",
  cold: "bg-cold/10 text-cold",
  success: "bg-success/10 text-success",
  primary: "bg-primary/10 text-primary",
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: keyof typeof badgeVariants;
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
        badgeVariants[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
