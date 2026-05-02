"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

const buttonVariants = {
  primary:
    "bg-primary text-white hover:bg-primary-dark focus:ring-2 focus:ring-primary/30 shadow-sm",
  secondary:
    "bg-background-secondary text-foreground-primary border border-border hover:border-primary/40 hover:bg-primary/5",
  ghost:
    "bg-transparent text-foreground-secondary hover:bg-background-secondary hover:text-foreground-primary",
  outline:
    "bg-transparent text-foreground-primary border border-border hover:border-primary hover:bg-primary/5",
  danger:
    "bg-hot text-white hover:bg-red-600 focus:ring-2 focus:ring-hot/30",
};

const buttonSizes = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
  lg: "h-11 px-6 text-sm",
  icon: "h-9 w-9 p-0",
};

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof buttonVariants;
  size?: keyof typeof buttonSizes;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading,
      leftIcon,
      rightIcon,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-all duration-fast focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none",
          buttonVariants[variant],
          buttonSizes[size],
          className
        )}
        {...props}
      >
        {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
        {!isLoading && leftIcon}
        {children}
        {!isLoading && rightIcon}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button };
