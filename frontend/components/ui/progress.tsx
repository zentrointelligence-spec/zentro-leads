"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
  variant?: "default" | "success" | "hot" | "primary";
}

const progressVariants = {
  default: "bg-primary",
  success: "bg-success",
  hot: "bg-hot",
  primary: "bg-primary",
};

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value, max = 100, variant = "default", ...props }, ref) => {
    const percentage = Math.min(100, Math.max(0, (value / max) * 100));

    return (
      <div
        ref={ref}
        className={cn(
          "relative h-2 w-full overflow-hidden rounded-full bg-background-secondary",
          className
        )}
        {...props}
      >
        <div
          className={cn("h-full rounded-full transition-all duration-500", progressVariants[variant])}
          style={{ width: `${percentage}%` }}
        />
      </div>
    );
  }
);
Progress.displayName = "Progress";

export { Progress };
