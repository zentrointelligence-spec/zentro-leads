"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
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

interface UserCookie {
  id: string;
  email: string;
  full_name: string;
  company_name: string | null;
  plan: string;
  avatar_url: string | null;
}

const navItems = [
  { href: "/dashboard",           label: "Dashboard",      icon: LayoutDashboard },
  { href: "/dashboard/leads",     label: "Leads",          icon: Users },
  { href: "/dashboard/icp",       label: "ICP Builder",    icon: Target },
  { href: "/dashboard/content",   label: "Content",        icon: FileText },
  { href: "/dashboard/broadcasts",label: "Broadcasts",     icon: Megaphone },
  { href: "/dashboard/pages",     label: "Landing Pages",  icon: Globe },
  { href: "/dashboard/settings",  label: "Settings",       icon: Settings },
];

function getCookieUser(): UserCookie | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/zentro_user=([^;]+)/);
  if (!match) return null;
  try {
    return JSON.parse(decodeURIComponent(match[1]));
  } catch {
    return null;
  }
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<UserCookie | null>(null);

  useEffect(() => {
    const u = getCookieUser();
    if (!u) {
      router.push("/login");
      return;
    }
    setUser(u);
  }, [router]);

  async function handleLogout() {
    await fetch("/api/v1/auth/logout", { method: "POST", credentials: "include" });
    router.push("/login");
  }

  return (
    <div className="flex h-screen bg-[#080f1a] text-white overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 bg-[#0F1B2D] border-r border-white/8 flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center px-5 border-b border-white/8">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#3B6FFF] flex items-center justify-center flex-shrink-0">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-white font-bold text-sm leading-none">Zentro Leads</p>
              <p className="text-slate-500 text-[10px] mt-0.5">AI Lead Generation</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active =
              href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  active
                    ? "bg-[#3B6FFF]/15 text-[#3B6FFF]"
                    : "text-slate-400 hover:text-white hover:bg-white/5"
                )}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* User */}
        {user && (
          <div className="border-t border-white/8 p-3">
            <div className="flex items-center gap-3 px-2 py-2">
              <div className="w-8 h-8 rounded-full bg-[#3B6FFF]/20 flex items-center justify-center flex-shrink-0">
                <span className="text-[#3B6FFF] text-xs font-bold uppercase">
                  {user.full_name?.[0] ?? "U"}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-white text-xs font-medium truncate">{user.full_name}</p>
                <p className="text-slate-500 text-[10px] truncate capitalize">{user.plan} plan</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 text-sm transition-colors mt-1"
            >
              <LogOut className="w-4 h-4" />
              Sign out
            </button>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="h-16 flex items-center px-6 border-b border-white/8 bg-[#0a1628] flex-shrink-0">
          <h1 className="text-white font-semibold text-base">
            {navItems.find((n) =>
              n.href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname.startsWith(n.href)
            )?.label ?? "Dashboard"}
          </h1>
        </header>
        <div className="flex-1 overflow-y-auto p-6">{children}</div>
      </main>
    </div>
  );
}
