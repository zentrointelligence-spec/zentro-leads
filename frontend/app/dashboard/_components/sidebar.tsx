"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import type { User } from "@/lib/api";
import {
  LayoutDashboard,
  Users,
  BarChart3,
  Settings,
  Sun,
  Moon,
  LogOut,
  ChevronRight,
  Kanban,
  UserCheck,
  Brain,
  ShieldAlert,
} from "lucide-react";
import { useTheme } from "@/app/providers/theme-provider";
import { Avatar } from "@/components/ui/avatar";

interface SidebarProps {
  user: User;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

const sections = [
  {
    title: "MAIN",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/dashboard/leads", label: "Leads", icon: Users },
      { href: "/dashboard/icp", label: "ICP Builder", icon: Brain },
      { href: "/dashboard/pipeline", label: "Pipeline", icon: Kanban },
      { href: "/dashboard/customers", label: "Customers", icon: UserCheck },
      { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
    ],
  },
  {
    title: "ACCOUNT",
    items: [
      { href: "/dashboard/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function Sidebar({ user, mobileOpen, onCloseMobile }: SidebarProps) {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();

  const isFree = user.plan === "free";
  const planLabel = isFree ? "Free Plan" : `${user.plan} Plan`;

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-50 flex h-full w-[260px] flex-col transition-transform duration-300 lg:static lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
        style={{ backgroundColor: "var(--sidebar-bg)" }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-orange-600 to-amber-500">
            <svg viewBox="0 0 44 44" className="h-5 w-5" aria-hidden="true">
              <path d="M12 13.5h17.6L14.4 30.5H32" fill="none" stroke="#0B1120" strokeWidth="4.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <div className="text-base font-black" style={{ color: "var(--sidebar-logo-text)" }}>Zentro Intelligence</div>
          </div>
        </div>

        {/* Plan badge */}
        <div className="mx-4 mb-3 flex items-center justify-between rounded-lg px-3 py-2" style={{ backgroundColor: "var(--sidebar-item-hover)", border: "1px solid var(--sidebar-border)" }}>
          <span className="text-xs font-medium" style={{ color: "var(--sidebar-plan-text)" }}>{planLabel}</span>
          {isFree && (
            <Link
              href="/dashboard/settings"
              className="inline-flex items-center gap-0.5 text-xs font-semibold transition-colors hover:opacity-80"
              style={{ color: "var(--color-brand)" }}
            >
              Upgrade <ChevronRight className="h-3 w-3" />
            </Link>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-2">
          <div className="space-y-5">
            {sections.map((section) => (
              <div key={section.title}>
                <p className="px-3 mb-1.5 text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--sidebar-logo-version)" }}>
                  {section.title}
                </p>
                <div className="space-y-0.5">
                  {section.items.map(({ href, label, icon: Icon }) => {
                    const active =
                      href === "/dashboard"
                        ? pathname === href
                        : pathname.startsWith(href);
                    return (
                      <Link
                        key={href}
                        href={href}
                        onClick={onCloseMobile}
                        className={cn(
                          "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all",
                          active
                            ? "text-white"
                            : "hover:text-white"
                        )}
                        style={
                          active
                            ? {
                                backgroundColor: "var(--sidebar-item-active)",
                                borderLeft: "2px solid var(--color-brand)",
                                marginLeft: "-2px",
                              }
                            : {
                                color: "var(--sidebar-text)",
                              }
                        }
                        onMouseEnter={(e) => {
                          if (!active) {
                            (e.currentTarget as HTMLElement).style.backgroundColor = "var(--sidebar-item-hover)";
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!active) {
                            (e.currentTarget as HTMLElement).style.backgroundColor = "transparent";
                          }
                        }}
                      >
                        <Icon className="h-4 w-4 flex-shrink-0" />
                        {label}
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </nav>

        {/* Admin Panel link — only shown to admin users */}
        {user.role === "admin" && (
          <div className="mt-4">
            <p className="px-3 mb-1.5 text-[10px] font-bold uppercase tracking-wider text-red-700">
              System
            </p>
            <Link
              href="/dashboard/admin"
              onClick={onCloseMobile}
              className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold transition-all text-red-400 hover:bg-red-950/40 hover:text-red-300"
            >
              <ShieldAlert className="h-4 w-4 flex-shrink-0" />
              Admin Panel
            </Link>
          </div>
        )}

        {/* Bottom section */}
        <div className="p-3 space-y-1" style={{ borderTop: "1px solid var(--sidebar-border)" }}>
          {/* Theme toggle */}
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors"
            style={{ color: "var(--sidebar-text)" }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.backgroundColor = "var(--sidebar-item-hover)";
              (e.currentTarget as HTMLElement).style.color = "var(--sidebar-text-active)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.backgroundColor = "transparent";
              (e.currentTarget as HTMLElement).style.color = "var(--sidebar-text)";
            }}
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>

          {/* Logout */}
          <button
            onClick={() => {
              fetch("/api/v1/auth/logout", {
                method: "POST",
                credentials: "include",
                keepalive: true,
              }).catch(() => {});
              window.location.href = "/login";
            }}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors"
            style={{ color: "var(--sidebar-text)" }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.backgroundColor = "var(--sidebar-item-hover)";
              (e.currentTarget as HTMLElement).style.color = "var(--sidebar-text-active)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.backgroundColor = "transparent";
              (e.currentTarget as HTMLElement).style.color = "var(--sidebar-text)";
            }}
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>

          {/* User */}
          <div className="flex items-center gap-3 rounded-md px-3 py-2">
            <Avatar name={user.full_name || "U"} size="sm" />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold truncate" style={{ color: "var(--sidebar-text-active)" }}>
                {user.full_name}
              </p>
              <p className="text-[10px] truncate" style={{ color: "var(--sidebar-text)" }}>
                {user.email}
              </p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
