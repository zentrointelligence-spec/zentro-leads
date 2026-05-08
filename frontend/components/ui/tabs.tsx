"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

function SimpleTabs({
  tabs,
  activeTab,
  onTabChange,
  className,
}: {
  tabs: { value: string; label: string; content: React.ReactNode }[];
  activeTab: string;
  onTabChange: (value: string) => void;
  className?: string;
}) {
  return (
    <div className={cn("w-full", className)}>
      <div className="inline-flex h-10 items-center rounded-lg bg-background-secondary p-1 gap-0.5">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => onTabChange(tab.value)}
            className={cn(
              "inline-flex items-center justify-center rounded-md px-4 py-1.5 text-sm font-medium transition-all",
              activeTab === tab.value
                ? "bg-card-bg text-foreground-primary shadow-sm"
                : "text-foreground-muted hover:text-foreground-primary"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="mt-6">
        {tabs.find((t) => t.value === activeTab)?.content}
      </div>
    </div>
  );
}

export { SimpleTabs };
