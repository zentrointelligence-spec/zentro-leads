"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import type { User } from "@/lib/api";
import {
  LayoutDashboard,
  Users,
  Building2,
  CheckSquare,
  Target,
  Globe,
  Megaphone,
  Brain,
  BarChart3,
  Zap,
  Settings,
  Plug,
  Sun,
  Moon,
  Radar,
  LogOut,
  ChevronRight,
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
    title: "OVERVIEW",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    ],
  },
  {
    title: "PIPELINE",
    items: [
      { href: "/dashboard/leads", label: "Leads", icon: Users },
      { href: "/dashboard/companies", label: "Companies", icon: Building2 },
      { href: "/dashboard/tasks", label: "Tasks", icon: CheckSquare },
    ],
  },
  {
    title: "CAPTURE",
    items: [
      { href: "/dashboard/icp", label: "ICP Builder", icon: Target },
      { href: "/dashboard/pages", label: "Landing Pages", icon: Globe },
      { href: "/dashboard/broadcasts", label: "Broadcasts", icon: Megaphone },
    ],
  },
  {
    title: "INTELLIGENCE",
    items: [
      { href: "/dashboard/ai-agents", label: "AI Agents", icon: Brain },
      { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
      { href: "/dashboard/automations", label: "Automations", icon: Zap },
    ],
  },
  {
    title: "ACCOUNT",
    items: [
      { href: "/dashboard/settings", label: "Settings", icon: Settings },
      { href: "/dashboard/integrations", label: "Integrations", icon: Plug },
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
          <div className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ backgroundColor: "var(--color-brand)" }}>
            <Radar className="h-4 w-4 text-white" />
          </div>
          <div>
            <div className="text-lg font-bold" style={{ color: "var(--sidebar-logo-text)" }}>LeadRadar</div>
            <div className="text-xs" style={{ color: "var(--sidebar-logo-version)" }}>v2.0</div>
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
