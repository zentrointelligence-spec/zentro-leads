"use client";

import { Plug } from "lucide-react";

export default function IntegrationsPage() {
  return (
    <div className="flex flex-col items-center justify-center h-[60vh] gap-4 animate-fade-in-up">
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center"
        style={{ backgroundColor: "var(--color-brand-bg)" }}
      >
        <Plug className="w-8 h-8" style={{ color: "var(--color-brand)" }} />
      </div>
      <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
        Integrations
      </h2>
      <p className="text-center max-w-md" style={{ color: "var(--text-secondary)" }}>
        Connect LeadRadar with your existing tools — coming soon.
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
