"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/cn";
import type { User } from "@/lib/api";
import {
  LayoutDashboard,
  Users,
  Target,
  FileText,
  Megaphone,
  Globe,
  Settings,
  LogOut,
  Zap,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/leads", label: "Leads", icon: Users },
  { href: "/dashboard/icp", label: "ICP Builder", icon: Target },
  { href: "/dashboard/content", label: "Content", icon: FileText },
  { href: "/dashboard/broadcasts", label: "Broadcasts", icon: Megaphone },
  { href: "/dashboard/pages", label: "Landing Pages", icon: Globe },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

interface Props {
  user: User;
  children: React.ReactNode;
}

export function DashboardShell({ user, children }: Props) {
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout() {
    await fetch("/api/v1/auth/logout", {
      method: "POST",
      credentials: "include",
    });
    router.push("/login");
    router.refresh();
  }

  const activeLabel =
    navItems.find((n) =>
      n.href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(n.href)
    )?.label ?? "Dashboard";

  return (
    <div className="flex h-screen overflow-hidden bg-[color:var(--bg-primary)] text-[color:var(--text-primary)]">
      <aside
        className={cn(
          "w-60 flex-shrink-0 flex flex-col border-r backdrop-blur-xl",
          "border-[color:var(--border-color)] bg-[color:var(--sidebar-bg)]"
        )}
      >
        <div className="h-16 flex items-center px-5 border-b border-[color:var(--border-color)]">
          <div className="flex items-center gap-2.5">
            <div
              className={cn(
                "w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0",
                "bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 shadow-md",
                "shadow-[0_0_20px_rgba(99,102,241,0.35)]"
              )}
            >
              <Zap className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-[color:var(--text-primary)] font-bold text-sm leading-none">
                Zentro Leads
              </p>
              <p className="text-[color:var(--text-muted)] text-[10px] mt-0.5">AI Lead Generation</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active =
              href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200",
                  active
                    ? "bg-[color:var(--accent-soft)] text-[color:var(--accent)] shadow-[0_0_20px_rgba(99,102,241,0.12)] border border-[color:var(--border-color)]"
                    : "text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)] hover:bg-[color:var(--accent-soft)]/50"
                )}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-[color:var(--border-color)] p-3">
          <div className="flex items-center gap-3 px-2 py-2">
            <div
              className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                "bg-[color:var(--accent-soft)] ring-1 ring-[color:var(--border-color)]"
              )}
            >
              <span className="text-[color:var(--accent)] text-xs font-bold uppercase">
                {user.full_name?.[0] ?? "U"}
              </span>
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[color:var(--text-primary)] text-xs font-medium truncate">
                {user.full_name}
              </p>
              <p className="text-[color:var(--text-muted)] text-[10px] truncate capitalize">
                {user.plan} plan
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-xl text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)] hover:bg-[color:var(--accent-soft)]/40 text-sm transition-colors mt-1"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header
          className={cn(
            "h-14 flex items-center px-6 border-b flex-shrink-0 backdrop-blur-xl",
            "border-[color:var(--border-color)] bg-[color:var(--header-bg)]"
          )}
        >
          <h1 className="text-[color:var(--text-primary)] font-semibold text-base tracking-tight">
            {activeLabel}
          </h1>
        </header>
        <div className="flex-1 overflow-y-auto p-6 bg-[color:var(--bg-primary)]">{children}</div>
      </main>
    </div>
  );
}
