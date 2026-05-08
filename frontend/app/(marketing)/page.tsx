"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BarChart3,
  Bell,
  Check,
  CheckCircle2,
  ChevronRight,
  FileText,
  MessageCircle,
  Search,
  Shield,
  Star,
  Users,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/cn";

const fadeUp = { hidden: { opacity: 0, y: 24 }, visible: { opacity: 1, y: 0, transition: { duration: 0.5 } } };
const stagger = { hidden: {}, visible: { transition: { staggerChildren: 0.08 } } };

// ── Shared Primitives ────────────────────────────────────────

function GlassCard({ children, className, glow }: { children: React.ReactNode; className?: string; glow?: "orange" | "emerald" | "amber" }) {
  return (
    <motion.div variants={fadeUp} className={cn(
      "rounded-2xl border border-white/[0.08] bg-white/[0.045] shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_20px_60px_rgba(0,0,0,0.22)] backdrop-blur-xl transition duration-300 hover:-translate-y-1",
      glow === "orange" && "hover:border-orange-400/30 hover:shadow-[0_24px_80px_rgba(234,88,12,0.16)]",
      glow === "emerald" && "hover:border-emerald-400/30 hover:shadow-[0_24px_80px_rgba(16,185,129,0.14)]",
      glow === "amber" && "hover:border-amber-400/30 hover:shadow-[0_24px_80px_rgba(245,158,11,0.14)]",
      className
    )}>
      {children}
    </motion.div>
  );
}

// ── Hero ─────────────────────────────────────────────────────

function HeroSection() {
  return (
    <section className="relative overflow-hidden px-5 pt-32 pb-16 sm:pt-40 lg:px-8 lg:pb-24">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(234,88,12,0.22),transparent_36%),radial-gradient(circle_at_15%_24%,rgba(245,158,11,0.12),transparent_28%),linear-gradient(180deg,#0B1120_0%,#0F172A_100%)]" />
      <div className="absolute inset-0 opacity-[0.10] [background-image:linear-gradient(rgba(255,255,255,.6)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.6)_1px,transparent_1px)] [background-size:72px_72px]" />

      <motion.div initial="hidden" animate="visible" variants={stagger} className="relative mx-auto max-w-5xl text-center">
        <motion.div variants={fadeUp} className="inline-flex items-center gap-2 rounded-full border border-orange-300/20 bg-orange-400/10 px-3 py-1.5 text-xs font-bold text-orange-200">
          <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.9)]" />
          Used by 200+ insurance agencies in Malaysia
        </motion.div>

        <motion.h1 variants={fadeUp} className="mx-auto mt-7 text-[42px] font-black leading-[1.03] tracking-tight text-white sm:text-6xl lg:text-[76px]">
          From Lead to Policy —<br />
          <span className="bg-gradient-to-r from-orange-400 via-amber-400 to-emerald-400 bg-clip-text text-transparent">Fully Automated</span>
        </motion.h1>

        <motion.p variants={fadeUp} className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-slate-300">
          Generate, qualify, and close insurance leads in one intelligent platform. Stop chasing cold lists — start closing warm prospects.
        </motion.p>

        <motion.div variants={fadeUp} className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link href="/register" className="inline-flex h-[52px] items-center justify-center rounded-xl bg-gradient-to-r from-orange-600 to-amber-500 px-7 text-base font-black text-white shadow-[0_16px_48px_rgba(234,88,12,0.38)] transition hover:-translate-y-0.5">
            Start Free Trial <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
          <Link href="#how-it-works" className="inline-flex h-[52px] items-center justify-center rounded-xl border border-white/12 bg-white/[0.04] px-7 text-base font-semibold text-white backdrop-blur-xl transition hover:bg-white/[0.08]">
            Watch Demo
          </Link>
        </motion.div>

        <motion.div variants={fadeUp} className="mx-auto mt-12 grid max-w-3xl grid-cols-2 gap-3 sm:grid-cols-4">
          {[["200+", "Agencies"], ["50K+", "Leads Generated"], ["91%", "Accuracy Rate"], ["3× Faster", "Than Manual"]].map(([val, lbl]) => (
            <div key={lbl} className="rounded-2xl border border-white/[0.08] bg-white/[0.04] px-4 py-4 backdrop-blur-xl">
              <div className="text-2xl font-black text-white sm:text-3xl">{val}</div>
              <div className="mt-1 text-xs font-medium text-slate-400">{lbl}</div>
            </div>
          ))}
        </motion.div>
      </motion.div>

      {/* Dashboard preview */}
      <motion.div initial={{ opacity: 0, y: 48 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5, duration: 0.7 }} className="relative mx-auto mt-16 max-w-5xl">
        <div className="absolute inset-0 rounded-3xl bg-gradient-to-b from-orange-500/10 via-transparent to-transparent blur-3xl" />
        <div className="relative overflow-hidden rounded-2xl border border-white/[0.08] bg-[#0d1425] shadow-[0_40px_120px_rgba(0,0,0,0.5)]">
          <div className="flex items-center gap-2 border-b border-white/[0.06] px-4 py-3">
            <span className="h-3 w-3 rounded-full bg-red-400/80" />
            <span className="h-3 w-3 rounded-full bg-amber-400/80" />
            <span className="h-3 w-3 rounded-full bg-emerald-400/80" />
            <span className="ml-3 text-xs text-slate-500">app.zentro.io/leads</span>
          </div>
          <div className="grid grid-cols-[200px_1fr] divide-x divide-white/[0.05] lg:grid-cols-[220px_1fr]">
            {/* Mock sidebar */}
            <div className="hidden p-4 md:block">
              <div className="mb-4 px-3 py-2 text-[10px] font-black tracking-widest text-slate-500">NAVIGATION</div>
              {[["Dashboard", true], ["Leads", false], ["Pipeline", false], ["Customers", false], ["Analytics", false]].map(([label, active]) => (
                <div key={label as string} className={cn("mb-1 flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold",
                  active ? "bg-orange-500/15 text-orange-300" : "text-slate-500"
                )}>
                  <span className={cn("h-1.5 w-1.5 rounded-full", active ? "bg-orange-400" : "bg-slate-700")} />
                  {label}
                </div>
              ))}
            </div>
            {/* Mock content */}
            <div className="p-5">
              <div className="mb-4 text-sm font-black text-white">Lead Intelligence</div>
              <div className="space-y-2">
                {[
                  ["Apex Risk Group", "Motor Fleet", "94", "HOT"],
                  ["Klang Valley Holdings", "Fire & Peril", "78", "WARM"],
                  ["Sunway Properties", "Liability", "82", "WARM"],
                ].map(([name, type, score, tier]) => (
                  <div key={name} className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.03] px-4 py-3">
                    <div>
                      <div className="text-xs font-semibold text-white">{name}</div>
                      <div className="text-[10px] text-slate-500">{type}</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-black text-white">{score}</span>
                      <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-black",
                        tier === "HOT" ? "bg-red-500/15 text-red-300" : "bg-amber-500/15 text-amber-300"
                      )}>{tier}</span>
                      <span className="rounded-lg bg-orange-500/15 px-2 py-1 text-[10px] font-black text-orange-300">Push →</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}

// ── How it works ─────────────────────────────────────────────

function HowItWorksSection() {
  const steps = [
    { n: "01", icon: Search, title: "Generate Leads", description: "AI scans live intent signals — tenders, SSM registrations, hiring activity — and surfaces ready-to-buy companies." },
    { n: "02", icon: Zap, title: "AI Qualifies Leads", description: "Every lead gets a 0-100 score based on company fit, role match, intent signals, and email verification." },
    { n: "03", icon: Users, title: "Push to CRM", description: "One click sends hot leads into your pipeline with pre-drafted WhatsApp and email outreach ready to send." },
    { n: "04", icon: Bell, title: "Follow-up Automation", description: "Scheduled reminders and broadcast sequences keep you top-of-mind without manual chasing." },
    { n: "05", icon: CheckCircle2, title: "Close Policy", description: "Track every deal from interested to converted. Analytics show what works so you close faster next cycle." },
  ];

  return (
    <section id="how-it-works" className="relative px-5 py-20 lg:px-8 lg:py-28">
      <div className="mx-auto max-w-7xl">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={stagger} className="mb-14 max-w-2xl">
          <motion.div variants={fadeUp} className="text-xs font-black uppercase tracking-[0.18em] text-orange-300">How It Works</motion.div>
          <motion.h2 variants={fadeUp} className="mt-3 text-4xl font-black text-white sm:text-5xl">Lead to Policy in 5 Steps</motion.h2>
          <motion.p variants={fadeUp} className="mt-4 text-base leading-7 text-slate-400">A clear, repeatable process that turns AI intelligence into closed business.</motion.p>
        </motion.div>

        <div className="relative">
          {/* Connector line */}
          <div className="absolute left-6 top-12 bottom-12 hidden w-px bg-gradient-to-b from-orange-500 via-amber-400 to-emerald-400 lg:left-1/2 lg:block" />

          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} variants={stagger} className="space-y-6 lg:space-y-0">
            {steps.map((step, i) => (
              <motion.div key={step.n} variants={fadeUp} className={cn("relative lg:flex lg:items-center lg:gap-12 lg:py-6", i % 2 === 0 ? "lg:flex-row" : "lg:flex-row-reverse")}>
                {/* Step card */}
                <div className={cn("relative z-10 w-full rounded-2xl border border-white/[0.08] bg-white/[0.04] p-6 backdrop-blur-xl lg:w-[calc(50%-40px)]",
                  "shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_16px_48px_rgba(0,0,0,0.18)]"
                )}>
                  <div className="flex items-start gap-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-orange-500/[0.14] text-orange-300">
                      <step.icon className="h-6 w-6" />
                    </div>
                    <div>
                      <div className="text-[10px] font-black tracking-widest text-orange-400">STEP {step.n}</div>
                      <h3 className="mt-1 text-lg font-black text-white">{step.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-slate-400">{step.description}</p>
                    </div>
                  </div>
                </div>

                {/* Center dot */}
                <div className="absolute left-[22px] hidden h-4 w-4 -translate-x-1/2 rounded-full border-2 border-orange-400 bg-[#0B1120] lg:left-1/2 lg:block" />
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}

// ── Features ─────────────────────────────────────────────────

function FeaturesSection() {
  const features = [
    [Zap, "AI Lead Generation", "Monitor live buying signals across tenders, hiring, SSM registrations, and renewal windows.", "orange"],
    [BarChart3, "Smart Lead Scoring", "Prioritise each company with transparent fit, urgency, and product-match scoring 0–100.", "amber"],
    [Users, "One-click Push to CRM", "Send any lead into your pipeline in one click with pre-drafted outreach messages.", "emerald"],
    [MessageCircle, "WhatsApp Automation", "Generate and schedule WhatsApp follow-ups tailored to each company's insurance need.", "orange"],
    [FileText, "Pipeline Tracking", "Kanban board tracks every deal from New Lead to Closed. Nothing falls through the cracks.", "amber"],
    [Shield, "Analytics Dashboard", "Daily digest, conversion rate, and revenue forecasts so you know what is working.", "emerald"],
  ] as const;

  return (
    <section id="features" className="relative px-5 py-20 lg:px-8 lg:py-28">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_50%,rgba(16,185,129,0.06),transparent_36%)]" />
      <div className="relative mx-auto max-w-7xl">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={stagger} className="mb-14 max-w-2xl">
          <motion.div variants={fadeUp} className="text-xs font-black uppercase tracking-[0.18em] text-orange-300">Features</motion.div>
          <motion.h2 variants={fadeUp} className="mt-3 text-4xl font-black text-white sm:text-5xl">Everything You Need to Close More Deals</motion.h2>
          <motion.p variants={fadeUp} className="mt-4 text-base leading-7 text-slate-400">Built for insurance professionals who want sharper prospecting and cleaner operations.</motion.p>
        </motion.div>
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} variants={stagger} className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {features.map(([Icon, title, description, glow]) => (
            <GlassCard key={title} glow={glow} className="p-6">
              <div className={cn("flex h-11 w-11 items-center justify-center rounded-xl",
                glow === "orange" ? "bg-orange-400/10 text-orange-300" : glow === "amber" ? "bg-amber-400/10 text-amber-300" : "bg-emerald-400/10 text-emerald-300"
              )}>
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="mt-5 text-lg font-black text-white">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-slate-400">{description}</p>
            </GlassCard>
          ))}
        </motion.div>
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} className="mt-10 text-center">
          <Link href="/features" className="inline-flex items-center gap-1 text-sm font-bold text-orange-300 transition hover:text-orange-200">
            See all features <ChevronRight className="h-4 w-4" />
          </Link>
        </motion.div>
      </div>
    </section>
  );
}

// ── Pricing preview ───────────────────────────────────────────

function PricingPreview() {
  const plans = [
    { name: "Starter", price: "$0", period: "/mo", desc: "CRM only", features: ["Manual lead entry", "Pipeline (up to 50 leads)", "Basic analytics"], highlight: false, cta: "Get Started" },
    { name: "Growth", price: "$49", period: "/mo", desc: "Most popular", features: ["AI lead generation (750 leads)", "Smart lead scoring", "WhatsApp broadcasts", "Pipeline + CRM", "Priority support"], highlight: true, cta: "Start Free Trial" },
    { name: "Pro", price: "$99", period: "/mo", desc: "Full power", features: ["10,000 leads/month", "Advanced analytics", "Full automation", "API access", "Dedicated support"], highlight: false, cta: "Start Free Trial" },
  ];

  return (
    <section id="pricing" className="relative px-5 py-20 lg:px-8 lg:py-28">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_60%,rgba(234,88,12,0.08),transparent_36%)]" />
      <div className="relative mx-auto max-w-7xl">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={stagger} className="mb-14 text-center">
          <motion.div variants={fadeUp} className="text-xs font-black uppercase tracking-[0.18em] text-orange-300">Pricing</motion.div>
          <motion.h2 variants={fadeUp} className="mt-3 text-4xl font-black text-white sm:text-5xl">Simple, Transparent Pricing</motion.h2>
          <motion.p variants={fadeUp} className="mx-auto mt-4 max-w-xl text-base leading-7 text-slate-400">Start free. Scale as your pipeline grows.</motion.p>
        </motion.div>
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} variants={stagger} className="grid gap-5 lg:grid-cols-3">
          {plans.map((plan) => (
            <motion.div key={plan.name} variants={fadeUp} className={cn(
              "relative rounded-2xl border p-7",
              plan.highlight
                ? "border-orange-400/40 bg-gradient-to-b from-orange-500/[0.12] to-transparent shadow-[0_24px_80px_rgba(234,88,12,0.18)]"
                : "border-white/[0.08] bg-white/[0.04]"
            )}>
              {plan.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-orange-600 to-amber-500 px-3 py-1 text-[11px] font-black text-white">
                  Most Popular
                </div>
              )}
              <div className="text-sm font-black uppercase tracking-widest text-slate-400">{plan.name}</div>
              <div className="mt-3 flex items-end gap-1">
                <span className="text-5xl font-black text-white">{plan.price}</span>
                <span className="mb-2 text-sm text-slate-400">{plan.period}</span>
              </div>
              <div className="mt-1 text-xs text-slate-500">{plan.desc}</div>
              <ul className="mt-7 space-y-3">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-slate-300">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link href="/register" className={cn(
                "mt-8 flex h-11 items-center justify-center rounded-xl text-sm font-black transition hover:-translate-y-0.5",
                plan.highlight
                  ? "bg-gradient-to-r from-orange-600 to-amber-500 text-white shadow-[0_12px_32px_rgba(234,88,12,0.32)]"
                  : "border border-white/10 bg-white/[0.04] text-white hover:bg-white/[0.08]"
              )}>
                {plan.cta}
              </Link>
            </motion.div>
          ))}
        </motion.div>
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} className="mt-8 text-center">
          <Link href="/pricing" className="inline-flex items-center gap-1 text-sm font-bold text-orange-300 transition hover:text-orange-200">
            Compare all plans <ChevronRight className="h-4 w-4" />
          </Link>
        </motion.div>
      </div>
    </section>
  );
}

// ── Testimonials ─────────────────────────────────────────────

function TestimonialsSection() {
  const testimonials = [
    ["We found 38 commercial motor prospects in our first week. The scoring helped our agents focus on the five that were actually ready to talk.", "Nur Afiqah", "Principal, Apex Risk Advisors"],
    ["The pipeline view cleaned up our renewal tracking. We stopped losing policies to missed follow-ups and now review every case daily.", "Marcus Lee", "Agency Director, Klang Valley General"],
    ["The WhatsApp drafts are specific enough that agents use them. Our fire insurance meetings doubled after targeting new factory registrations.", "Siti Hajar", "Founder, Hajar Assurance Partners"],
  ];

  return (
    <section className="relative px-5 py-20 lg:px-8 lg:py-28">
      <div className="mx-auto max-w-7xl">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={stagger} className="mb-14 max-w-2xl">
          <motion.div variants={fadeUp} className="text-xs font-black uppercase tracking-[0.18em] text-orange-300">Trust</motion.div>
          <motion.h2 variants={fadeUp} className="mt-3 text-4xl font-black text-white sm:text-5xl">Trusted by Professionals</motion.h2>
        </motion.div>
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} variants={stagger} className="grid gap-5 lg:grid-cols-3">
          {testimonials.map(([quote, name, company]) => (
            <GlassCard key={name as string} className="p-6">
              <div className="flex gap-0.5 text-amber-400">
                {Array.from({ length: 5 }).map((_, i) => <Star key={i} className="h-3.5 w-3.5 fill-current" />)}
              </div>
              <p className="mt-5 text-sm leading-7 text-slate-300">&ldquo;{quote}&rdquo;</p>
              <div className="mt-6 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-orange-600 to-amber-500 text-xs font-black text-white">
                  {(name as string).split(" ").map((p: string) => p[0]).join("").slice(0, 2)}
                </div>
                <div>
                  <div className="text-sm font-black text-white">{name}</div>
                  <div className="text-xs text-slate-500">{company}</div>
                </div>
              </div>
            </GlassCard>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

// ── CTA ──────────────────────────────────────────────────────

function CtaSection() {
  return (
    <section className="relative px-5 py-20 lg:px-8 lg:py-28">
      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="relative mx-auto max-w-5xl overflow-hidden rounded-3xl border border-orange-300/[0.18] bg-white/[0.04] px-6 py-16 text-center backdrop-blur-xl">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(234,88,12,0.28),transparent_44%)]" />
        <div className="relative">
          <motion.h2 variants={fadeUp} className="text-4xl font-black text-white sm:text-5xl">Ready to Automate Your Pipeline?</motion.h2>
          <motion.p variants={fadeUp} className="mx-auto mt-4 max-w-lg text-base leading-7 text-slate-300">Join 200+ agencies already closing faster with Zentro Intelligence.</motion.p>
          <motion.div variants={fadeUp} className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Link href="/register" className="inline-flex h-[52px] items-center justify-center rounded-xl bg-white px-7 text-base font-black text-slate-950 transition hover:-translate-y-0.5">
              Start Free Trial
            </Link>
            <Link href="mailto:sales@zentro.io" className="inline-flex h-[52px] items-center justify-center rounded-xl border border-white/20 bg-white/10 px-7 text-base font-semibold text-white backdrop-blur-xl">
              Talk to Sales
            </Link>
          </motion.div>
          <motion.p variants={fadeUp} className="mt-4 text-xs text-slate-500">No credit card required · 50 free leads · Cancel anytime</motion.p>
        </div>
      </motion.div>
    </section>
  );
}

// ── Page ─────────────────────────────────────────────────────

export default function MarketingPage() {
  return (
    <main className="overflow-hidden">
      <HeroSection />
      <HowItWorksSection />
      <FeaturesSection />
      <PricingPreview />
      <TestimonialsSection />
      <CtaSection />
    </main>
  );
}
