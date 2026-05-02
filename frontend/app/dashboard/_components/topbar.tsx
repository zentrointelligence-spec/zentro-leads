"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/cn";
import type { User } from "@/lib/api";
import { Search, Bell, Menu, LogOut, Settings } from "lucide-react";
import { Avatar } from "@/components/ui/avatar";

interface TopbarProps {
  user: User;
  title: string;
  subtitle?: string;
  onMenuClick: () => void;
}

export function Topbar({ user, title, subtitle, onMenuClick }: TopbarProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const handleLogout = useCallback(() => {
    setOpen(false);
    fetch("/api/v1/auth/logout", {
      method: "POST",
      credentials: "include",
      keepalive: true,
    }).catch(() => {});
    window.location.href = "/login";
  }, []);

  return (
    <header
      className="flex h-[64px] items-center justify-between px-4 lg:px-6 backdrop-blur-xl"
      style={{
        backgroundColor: "var(--bg-primary)",
        borderBottom: "1px solid var(--border-primary)",
      }}
    >
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="rounded-lg p-2 lg:hidden"
          style={{ color: "var(--text-secondary)" }}
        >
          <Menu className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>
            {title}
          </h1>
          {subtitle && (
            <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
              {subtitle}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Search */}
        <div
          className="hidden md:flex items-center gap-2 rounded-lg px-3 py-2"
          style={{
            backgroundColor: "var(--bg-secondary)",
            border: "1px solid var(--border-primary)",
          }}
        >
          <Search className="h-4 w-4" style={{ color: "var(--text-tertiary)" }} />
          <input
            type="text"
            placeholder="Search..."
            className="w-44 bg-transparent text-sm outline-none"
            style={{ color: "var(--text-primary)" }}
          />
        </div>

        {/* Notifications */}
        <button
          className="relative rounded-lg p-2.5 transition-colors"
          style={{ color: "var(--text-secondary)" }}
        >
          <Bell className="h-5 w-5" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full" style={{ backgroundColor: "var(--color-brand)" }} />
        </button>

        {/* User menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setOpen((v) => !v);
            }}
            className="flex items-center gap-2 rounded-lg p-1 transition-colors"
            style={{
              backgroundColor: open ? "var(--bg-hover)" : "transparent",
            }}
          >
            <Avatar name={user.full_name || "U"} size="sm" />
          </button>

          {open && (
            <div
              className="absolute right-0 top-full z-50 mt-2 w-56 rounded-xl py-1.5 shadow-xl"
              style={{
                backgroundColor: "var(--bg-card)",
                border: "1px solid var(--border-primary)",
              }}
            >
              <div className="px-4 py-2.5" style={{ borderBottom: "1px solid var(--border-primary)" }}>
                <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
                  {user.full_name}
                </p>
                <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>{user.email}</p>
              </div>
              <button
                onClick={() => {
                  setOpen(false);
                  router.push("/dashboard/settings");
                }}
                className="flex w-full items-center gap-2.5 px-4 py-2.5 text-sm transition-colors"
                style={{ color: "var(--text-secondary)" }}
              >
                <Settings className="h-4 w-4" />
                Settings
              </button>
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2.5 px-4 py-2.5 text-sm transition-colors"
                style={{ color: "var(--text-secondary)" }}
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
