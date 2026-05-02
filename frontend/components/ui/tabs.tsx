"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

interface TabsProps {
  value: string;
  onChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

function Tabs({ value, onChange, children, className }: TabsProps) {
  return (
    <div className={cn("w-full", className)}>
      {React.Children.map(children, (child) =>
        React.isValidElement(child)
          ? React.cloneElement(child as React.ReactElement<{ value?: string; onChange?: (v: string) => void }>, {
              value,
              onChange,
            })
          : child
      )}
    </div>
  );
}

interface TabsListProps {
  children: React.ReactNode;
  className?: string;
}

function TabsList({ children, className }: TabsListProps) {
  return (
    <div
      className={cn(
        "inline-flex h-10 items-center justify-start rounded-md bg-background-secondary p-1 gap-1",
        className
      )}
    >
      {children}
    </div>
  );
}

interface TabsTriggerProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

function TabsTrigger({ value: triggerValue, children, className }: TabsTriggerProps) {
  return (
    <button
      type="button"
      onClick={() => {
        // Parent injects onChange via cloneElement
        // This is a simplified implementation
      }}
      className={cn(
        "inline-flex items-center justify-center rounded-sm px-3 py-1.5 text-sm font-medium transition-all",
        "text-foreground-muted hover:text-foreground-primary",
        "data-[state=active]:bg-card-bg data-[state=active]:text-foreground-primary data-[state=active]:shadow-sm",
        className
      )}
    />
  );
}

interface TabsContentProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

const TabsContext = React.createContext<{ value?: string; onChange?: (v: string) => void }>({});

function TabsContent({ value: contentValue, children, className }: TabsContentProps) {
  const ctx = React.useContext(TabsContext);
  if (ctx.value !== contentValue) return null;
  return <div className={cn("mt-4", className)}>{children}</div>;
}

// Simplified working Tabs implementation
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
