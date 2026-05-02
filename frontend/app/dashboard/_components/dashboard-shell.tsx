"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import type { User } from "@/lib/api";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

interface Props {
  user: User;
  children: React.ReactNode;
}

const pageMeta: Record<string, { title: string; subtitle?: string }> = {
  "/dashboard": { title: "Dashboard", subtitle: "Overview of your pipeline" },
  "/dashboard/leads": { title: "Lead Intelligence", subtitle: "AI-powered insights to close faster" },
  "/dashboard/icp": { title: "ICP Builder", subtitle: "Define your ideal customer profile" },
  "/dashboard/content": { title: "Content", subtitle: "AI-generated sales content" },
  "/dashboard/broadcasts": { title: "Broadcasts", subtitle: "WhatsApp and email campaigns" },
  "/dashboard/pages": { title: "Landing Pages", subtitle: "Lead capture pages and forms" },
  "/dashboard/settings": { title: "Settings", subtitle: "Manage your account and preferences" },
};

export function DashboardShell({ user, children }: Props) {
  const pathname = usePathname();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const meta =
    Object.entries(pageMeta).find(([path]) =>
      path === "/dashboard" ? pathname === path : pathname.startsWith(path)
    )?.[1] ?? { title: "Dashboard" };

  return (
    <div className="flex h-screen overflow-hidden bg-background-primary">
      <Sidebar
        user={user}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      <main className="flex flex-1 flex-col min-w-0 overflow-hidden">
        <Topbar
          user={user}
          title={meta.title}
          subtitle={meta.subtitle}
          onMenuClick={() => setMobileSidebarOpen(true)}
        />
        <div className="flex-1 overflow-y-auto bg-background-primary p-4 lg:p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
