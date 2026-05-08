"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/cn";

export function ZentroLogo({ variant = "color" }: { variant?: "color" | "white" }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className={cn(
        "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border",
        variant === "color"
          ? "border-orange-400/30 bg-gradient-to-br from-orange-600 via-amber-500 to-emerald-500 shadow-[0_0_24px_rgba(234,88,12,0.35)]"
          : "border-white/20 bg-white/10"
      )}>
        <svg viewBox="0 0 44 44" className="h-7 w-7" aria-hidden="true">
          <path d="M12 13.5h17.6L14.4 30.5H32" fill="none" stroke="#0B1120" strokeWidth="4.8" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M28 11c5.1 2.1 8 6 8 11s-2.9 8.9-8 11" fill="none" stroke="#fff7ed" strokeWidth="2" strokeLinecap="round" opacity=".95" />
          <path d="M31.5 6.5C38.4 9.7 42 15.2 42 22s-3.6 12.3-10.5 15.5" fill="none" stroke="#10B981" strokeWidth="2" strokeLinecap="round" opacity=".9" />
        </svg>
      </div>
      <div className="leading-none">
        <div className="text-[17px] font-black tracking-tight text-white">Zentro</div>
        <div className="-mt-0.5 text-[9px] font-semibold tracking-[0.2em] text-slate-400">INTELLIGENCE</div>
      </div>
    </div>
  );
}

const NAV_LINKS = [
  { label: "Features", href: "/features" },
  { label: "Pricing", href: "/pricing" },
  { label: "How it works", href: "/#how-it-works" },
];

export function MarketingNav() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 10);
    fn();
    window.addEventListener("scroll", fn);
    return () => window.removeEventListener("scroll", fn);
  }, []);

  return (
    <header className={cn(
      "fixed inset-x-0 top-0 z-50 border-b transition-all duration-300",
      scrolled
        ? "border-white/10 bg-[#0b1120]/85 shadow-[0_16px_48px_rgba(0,0,0,0.26)] backdrop-blur-2xl"
        : "border-transparent bg-transparent"
    )}>
      <nav className="mx-auto flex h-[68px] max-w-7xl items-center justify-between px-5 lg:px-8">
        <Link href="/" aria-label="Zentro Intelligence home">
          <ZentroLogo />
        </Link>

        <div className="hidden items-center gap-7 md:flex">
          {NAV_LINKS.map(({ label, href }) => (
            <Link key={label} href={href} className="text-sm font-medium text-slate-300 transition-colors hover:text-white">
              {label}
            </Link>
          ))}
        </div>

        <div className="hidden items-center gap-4 md:flex">
          <Link href="/login" className="text-sm font-semibold text-slate-300 transition-colors hover:text-white">
            Sign in
          </Link>
          <Link
            href="/register"
            className="inline-flex h-9 items-center rounded-xl bg-gradient-to-r from-orange-600 to-amber-500 px-4 text-sm font-bold text-white shadow-[0_10px_28px_rgba(234,88,12,0.32)] transition hover:-translate-y-0.5"
          >
            Start Free Trial
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-white md:hidden"
          aria-label="Toggle navigation"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </nav>

      {open && (
        <div className="border-t border-white/10 bg-[#0b1120]/96 px-5 py-6 backdrop-blur-2xl md:hidden">
          <div className="space-y-4">
            {NAV_LINKS.map(({ label, href }) => (
              <Link key={label} href={href} onClick={() => setOpen(false)} className="block text-sm font-semibold text-slate-200">
                {label}
              </Link>
            ))}
            <div className="grid gap-3 pt-3">
              <Link href="/login" onClick={() => setOpen(false)} className="inline-flex h-11 items-center justify-center rounded-xl border border-white/10 text-sm font-bold text-white">
                Sign in
              </Link>
              <Link href="/register" onClick={() => setOpen(false)} className="inline-flex h-11 items-center justify-center rounded-xl bg-gradient-to-r from-orange-600 to-amber-500 text-sm font-bold text-white">
                Start Free Trial
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
