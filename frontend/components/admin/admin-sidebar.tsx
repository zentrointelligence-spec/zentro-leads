"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  BarChart2,
  Activity,
  ArrowLeft,
  ShieldAlert,
} from "lucide-react";
import { cn } from "@/lib/cn";

const NAV_ITEMS = [
  { href: "/dashboard/admin",        label: "Overview",      icon: LayoutDashboard, exact: true },
  { href: "/dashboard/admin/users",  label: "Users",         icon: Users },
  { href: "/dashboard/admin/leads",  label: "Lead Quality",  icon: BarChart2 },
  { href: "/dashboard/admin/system", label: "System Health", icon: Activity },
];

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-[240px] flex-col bg-gray-950 border-r border-gray-800 flex-shrink-0">
      {/* Header */}
      <div className="px-4 pt-5 pb-3 border-b border-gray-800">
        <div className="flex items-center gap-2 mb-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-red-600">
            <ShieldAlert className="h-4 w-4 text-white" />
          </div>
          <span className="text-xs font-black tracking-widest text-red-400 uppercase">
            Admin Panel
          </span>
        </div>
        <Link
          href="/dashboard"
          className="flex items-center gap-2 text-xs text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Dashboard
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <p className="px-2 mb-2 text-[10px] font-bold uppercase tracking-widest text-gray-600">
          Navigation
        </p>
        <div className="space-y-0.5">
          {NAV_ITEMS.map(({ href, label, icon: Icon, exact }) => {
            const isExactActive = pathname === href;
            const isActive = exact ? isExactActive : pathname.startsWith(href);

            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-gray-800 text-white"
                    : "text-gray-400 hover:bg-gray-800 hover:text-white"
                )}
                style={
                  isActive
                    ? { borderLeft: "2px solid #ef4444", marginLeft: "-2px" }
                    : {}
                }
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                {label}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-800">
        <p className="text-[10px] text-gray-600 text-center">
          Zentro Intelligence — Internal
        </p>
      </div>
    </aside>
  );
}
