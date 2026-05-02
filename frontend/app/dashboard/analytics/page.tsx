"use client";

import { BarChart3 } from "lucide-react";

export default function AnalyticsPage() {
  return (
    <div className="flex flex-col items-center justify-center h-[60vh] gap-4 animate-fade-in-up">
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center"
        style={{ backgroundColor: "var(--color-brand-bg)" }}
      >
        <BarChart3 className="w-8 h-8" style={{ color: "var(--color-brand)" }} />
      </div>
      <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
        Analytics
      </h2>
      <p className="text-center max-w-md" style={{ color: "var(--text-secondary)" }}>
        Deep insights into your lead pipeline performance — coming soon.
      </p>
      <span
        className="px-3 py-1 rounded-full text-sm font-medium"
        style={{ backgroundColor: "var(--color-brand-bg)", color: "var(--color-brand)" }}
      >
        Coming Soon
      </span>
    </div>
  );
}
