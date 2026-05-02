"use client";

import { CheckSquare } from "lucide-react";

export default function TasksPage() {
  return (
    <div className="flex flex-col items-center justify-center h-[60vh] gap-4 animate-fade-in-up">
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center"
        style={{ backgroundColor: "var(--color-brand-bg)" }}
      >
        <CheckSquare className="w-8 h-8" style={{ color: "var(--color-brand)" }} />
      </div>
      <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
        Tasks
      </h2>
      <p className="text-center max-w-md" style={{ color: "var(--text-secondary)" }}>
        Manage your follow-up tasks and reminders — coming soon.
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
