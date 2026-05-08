"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BarChart3,
  Bell,
  CheckCircle2,
  FileText,
  MessageCircle,
  Search,
  Shield,
  Users,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/cn";

const fadeUp = { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0, transition: { duration: 0.45 } } };
const stagger = { hidden: {}, visible: { transition: { staggerChildren: 0.07 } } };

const groups = [
  {
    section: "Lead Engine",
    color: "orange" as const,
    items: [
      {
        icon: Search,
        title: "AI Lead Generation",
        description: "Monitor live buying signals — tenders, SSM new registrations, hiring spikes, renewal windows. Surface companies that are actively in the market before your competitors do.",
        bullets: ["Google Maps + tender board scrapers", "6 intent signal monitors running 24/7", "ICP Builder: one sentence → structured profile", "New leads delivered to your dashboard daily"],
      },
      {
        icon: Zap,
        title: "Smart Lead Scoring",
        description: "Every lead is scored 0–100 using a transparent, deterministic engine based on company fit, role seniority, email verification, and intent strength.",
        bullets: ["Company size match (+30)", "Role and seniority match (+25)", "Industry match (+20)", "Intent signal bonus (+15)", "Verified email (+10)"],
      },
    ],
  },
  {
    section: "CRM & Pipeline",
    color: "amber" as const,
    items: [
      {
        icon: Users,
        title: "Pipeline Kanban",
        description: "Visual drag-and-drop pipeline with New Lead, Contacted, Interested, and Closed columns. Every deal stays visible. Nothing falls through the cracks.",
        bullets: ["Drag-and-drop stage management", "Push leads directly from Lead Engine", "Per-deal notes and activity log", "Filter by score, tier, and agent"],
      },
      {
        icon: FileText,
        title: "Customer Records",
        description: "Converted customers get a full profile: policy details, renewal dates, follow-up tasks, and communication history all in one place.",
        bullets: ["Policy number and premium tracking", "Renewal date reminders", "Document uploads (PDFs, images)", "Task and follow-up scheduler"],
      },
    ],
  },
  {
    section: "Automation & Outreach",
    color: "emerald" as const,
    items: [
      {
        icon: MessageCircle,
        title: "WhatsApp Automation",
        description: "AI generates WhatsApp messages tailored to each company's industry, buying signal, and insurance need. Agents send in one click — or schedule for later.",
        bullets: ["Industry-specific message templates", "Signal-aware personalisation", "Broadcast campaigns (bulk send)", "Reply tracking and thread view"],
      },
      {
        icon: Bell,
        title: "Daily Digest & Alerts",
        description: "Start every day with a curated list of hot leads, overdue follow-ups, and renewal reminders. Real-time alerts when a monitored company triggers a new signal.",
        bullets: ["Morning digest email + in-app", "Real-time signal push notifications", "Overdue task escalation", "New lead alerts by tier"],
      },
    ],
  },
  {
    section: "Analytics & Insights",
    color: "orange" as const,
    items: [
      {
        icon: BarChart3,
        title: "Analytics Dashboard",
        description: "Conversion rates, revenue forecast, lead-to-close velocity, and top-performing channels — all updated in real time.",
        bullets: ["Lead generation vs. conversion funnel", "Agent performance leaderboard", "Revenue by policy type", "Monthly and quarterly trend view"],
      },
      {
        icon: Shield,
        title: "Data Quality & Compliance",
        description: "Built-in email verification (SMTP), suppression lists, and audit logs keep your database clean and your outreach compliant.",
        bullets: ["SMTP email verification (no third-party APIs)", "Suppression list management", "Full audit trail per lead", "PDPA-aligned data handling"],
      },
    ],
  },
];

function Pill({ color, label }: { color: "orange" | "amber" | "emerald"; label: string }) {
  return (
    <span className={cn("inline-flex items-center rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-widest",
      color === "orange" && "bg-orange-400/10 text-orange-300",
      color === "amber" && "bg-amber-400/10 text-amber-300",
      color === "emerald" && "bg-emerald-400/10 text-emerald-300",
    )}>
      {label}
    </span>
  );
}

export default function FeaturesPage() {
  return (
    <main className="min-h-screen bg-[#0B1120] px-5 pt-28 pb-24 text-white lg:px-8">
      {/* Header */}
      <div className="mx-auto max-w-3xl text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.div variants={fadeUp} className="text-xs font-black uppercase tracking-[0.18em] text-orange-300">Platform Features</motion.div>
          <motion.h1 variants={fadeUp} className="mt-3 text-5xl font-black leading-tight text-white lg:text-6xl">Everything in One Platform</motion.h1>
          <motion.p variants={fadeUp} className="mx-auto mt-5 max-w-xl text-lg text-slate-400">
            From AI lead generation to closed policy — every tool you need lives inside Zentro Intelligence.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Link href="/register" className="inline-flex h-[50px] items-center justify-center rounded-xl bg-gradient-to-r from-orange-600 to-amber-500 px-6 text-sm font-black text-white shadow-[0_12px_32px_rgba(234,88,12,0.32)] transition hover:-translate-y-0.5">
              Start Free Trial <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link href="/pricing" className="inline-flex h-[50px] items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] px-6 text-sm font-semibold text-white transition hover:bg-white/[0.08]">
              View Pricing
            </Link>
          </motion.div>
        </motion.div>
      </div>

      {/* Feature groups */}
      <div className="mx-auto mt-24 max-w-6xl space-y-20">
        {groups.map((group) => (
          <div key={group.section}>
            <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} variants={stagger}>
              <motion.div variants={fadeUp} className="mb-10">
                <Pill color={group.color} label={group.section} />
              </motion.div>
              <div className="grid gap-6 md:grid-cols-2">
                {group.items.map((item) => (
                  <motion.div key={item.title} variants={fadeUp} className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-7 transition duration-300 hover:-translate-y-1">
                    <div className={cn("flex h-12 w-12 items-center justify-center rounded-xl",
                      group.color === "orange" ? "bg-orange-400/10 text-orange-300" :
                      group.color === "amber" ? "bg-amber-400/10 text-amber-300" :
                      "bg-emerald-400/10 text-emerald-300"
                    )}>
                      <item.icon className="h-6 w-6" />
                    </div>
                    <h3 className="mt-5 text-xl font-black text-white">{item.title}</h3>
                    <p className="mt-3 text-sm leading-7 text-slate-400">{item.description}</p>
                    <ul className="mt-5 space-y-2.5">
                      {item.bullets.map((b) => (
                        <li key={b} className="flex items-start gap-2.5 text-sm text-slate-300">
                          <CheckCircle2 className={cn("mt-0.5 h-4 w-4 shrink-0",
                            group.color === "orange" ? "text-orange-400" :
                            group.color === "amber" ? "text-amber-400" :
                            "text-emerald-400"
                          )} />
                          {b}
                        </li>
                      ))}
                    </ul>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>
        ))}
      </div>

      {/* Bottom CTA */}
      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} className="mx-auto mt-24 max-w-2xl rounded-2xl border border-orange-300/20 bg-orange-500/[0.07] p-10 text-center">
        <h2 className="text-2xl font-black text-white">See it in action</h2>
        <p className="mt-3 text-sm leading-7 text-slate-400">50 free leads. No credit card. Set up in under 5 minutes.</p>
        <Link href="/register" className="mt-6 inline-flex h-11 items-center justify-center rounded-xl bg-gradient-to-r from-orange-600 to-amber-500 px-6 text-sm font-black text-white shadow-[0_10px_28px_rgba(234,88,12,0.28)] transition hover:-translate-y-0.5">
          Start Free Trial
        </Link>
      </motion.div>

      <div className="mt-10 text-center">
        <Link href="/" className="text-sm text-slate-500 transition hover:text-slate-300">← Back to home</Link>
      </div>
    </main>
  );
}
