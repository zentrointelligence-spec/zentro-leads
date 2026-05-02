"use client";

import * as React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
  title?: string;
}

function Drawer({ open, onClose, children, className, title }: DrawerProps) {
  React.useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      <div
        className={cn(
          "absolute right-0 top-0 h-full w-full max-w-xl border-l border-card-border bg-card-bg shadow-2xl flex flex-col",
          "animate-in slide-in-from-right duration-300",
          className
        )}
      >
        {(title) && (
          <div className="flex items-center justify-between border-b border-border px-5 py-4 flex-shrink-0">
            {title && (
              <h3 className="text-base font-semibold text-foreground-primary">
                {title}
              </h3>
            )}
            <button
              onClick={onClose}
              className="ml-auto rounded-md p-1.5 text-foreground-muted hover:bg-background-secondary hover:text-foreground-primary transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        <div className="flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}

export { Drawer };
