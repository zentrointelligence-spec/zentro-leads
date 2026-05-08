import Link from "next/link";
import { Linkedin, X } from "lucide-react";
import { ZentroLogo } from "./nav";

export function MarketingFooter() {
  return (
    <footer className="border-t border-white/[0.08] bg-[#0B1120] px-5 py-14 lg:px-8">
      <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div>
          <ZentroLogo variant="white" />
          <p className="mt-5 max-w-xs text-sm leading-6 text-slate-400">
            AI-powered lead generation and pipeline management for insurance professionals across Southeast Asia.
          </p>
          <div className="mt-5 flex gap-3">
            <a href="https://x.com" aria-label="X" className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 text-slate-300 transition hover:border-white/20 hover:text-white">
              <X className="h-4 w-4" />
            </a>
            <a href="https://linkedin.com" aria-label="LinkedIn" className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 text-slate-300 transition hover:border-white/20 hover:text-white">
              <Linkedin className="h-4 w-4" />
            </a>
          </div>
        </div>

        {([
          ["Platform", [["Features", "/features"], ["Pricing", "/pricing"], ["How it works", "/#how-it-works"]]],
          ["Company", [["About", "#"], ["Blog", "#"], ["Contact", "#"]]],
          ["Legal", [["Privacy Policy", "#"], ["Terms of Service", "#"], ["Security", "#"]]],
        ] as [string, [string, string][]][]).map(([heading, items]) => (
          <div key={heading}>
            <h3 className="text-sm font-black text-white">{heading}</h3>
            <div className="mt-4 space-y-3">
              {items.map(([label, href]) => (
                <Link key={label} href={href} className="block text-sm text-slate-400 transition hover:text-white">
                  {label}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mx-auto mt-10 max-w-7xl border-t border-white/[0.06] pt-6 text-xs text-slate-600">
        © 2026 Zentro Intelligence Sdn Bhd
      </div>
    </footer>
  );
}
