"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Check, X } from "lucide-react";
import { cn } from "@/lib/cn";

const fadeUp = { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0, transition: { duration: 0.45 } } };
const stagger = { hidden: {}, visible: { transition: { staggerChildren: 0.07 } } };

const plans = [
  {
    name: "Starter",
    price: "$0",
    period: "/month",
    tagline: "CRM-only plan — manual leads",
    highlight: false,
    features: [
      { label: "Manual lead entry", included: true },
      { label: "Pipeline (up to 50 leads)", included: true },
      { label: "Basic analytics", included: true },
      { label: "WhatsApp templates", included: true },
      { label: "AI lead generation", included: false },
      { label: "Smart scoring", included: false },
      { label: "Broadcast campaigns", included: false },
      { label: "API access", included: false },
    ],
    cta: "Get Started Free",
  },
  {
    name: "Growth",
    price: "$49",
    period: "/month",
    tagline: "Lead Engine + CRM · 750 credits/mo",
    highlight: true,
    features: [
      { label: "750 AI-generated leads/month", included: true },
      { label: "Smart lead scoring (0–100)", included: true },
      { label: "Full pipeline + CRM", included: true },
      { label: "WhatsApp automation", included: true },
      { label: "Broadcast campaigns (2,000 sends)", included: true },
      { label: "Analytics dashboard", included: true },
      { label: "API access", included: false },
      { label: "Dedicated account manager", included: false },
    ],
    cta: "Start Free Trial",
  },
  {
    name: "Pro",
    price: "$99",
    period: "/month",
    tagline: "Full automation · 10,000 credits/mo",
    highlight: false,
    features: [
      { label: "10,000 AI-generated leads/month", included: true },
      { label: "Smart lead scoring (0–100)", included: true },
      { label: "Full pipeline + CRM", included: true },
      { label: "WhatsApp automation", included: true },
      { label: "Unlimited broadcast campaigns", included: true },
      { label: "Advanced analytics + forecasting", included: true },
      { label: "Full API access", included: true },
      { label: "Dedicated account manager", included: true },
    ],
    cta: "Start Free Trial",
  },
];

const faqs = [
  ["What counts as a lead credit?", "One credit = one AI-enriched lead profile (company + decision maker + email + score). Re-generating an existing lead does not use a new credit."],
  ["Can I change plans anytime?", "Yes. Upgrade or downgrade at any billing cycle. Unused credits do not roll over."],
  ["Is there a long-term contract?", "No. All plans are billed monthly. Cancel anytime from your settings page."],
  ["Do you support team accounts?", "Growth and Pro plans support multiple seats. Contact us for agency-wide pricing."],
  ["What payment methods do you accept?", "Visa, Mastercard, and FPX. Invoice billing is available for Pro plans."],
];

export default function PricingPage() {
  return (
    <main className="min-h-screen bg-[#0B1120] px-5 pt-28 pb-24 text-white lg:px-8">
      {/* Header */}
      <div className="mx-auto max-w-3xl text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.div variants={fadeUp} className="text-xs font-black uppercase tracking-[0.18em] text-orange-300">Pricing</motion.div>
          <motion.h1 variants={fadeUp} className="mt-3 text-5xl font-black leading-tight text-white lg:text-6xl">Simple, Honest Pricing</motion.h1>
          <motion.p variants={fadeUp} className="mx-auto mt-5 max-w-lg text-lg text-slate-400">
            Start free. Scale as your pipeline grows. No hidden fees.
          </motion.p>
        </motion.div>
      </div>

      {/* Plans */}
      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} variants={stagger} className="mx-auto mt-16 grid max-w-6xl gap-5 lg:grid-cols-3">
        {plans.map((plan) => (
          <motion.div key={plan.name} variants={fadeUp} className={cn(
            "relative rounded-2xl border p-8",
            plan.highlight
              ? "border-orange-400/40 bg-gradient-to-b from-orange-500/[0.1] to-transparent shadow-[0_28px_80px_rgba(234,88,12,0.18)]"
              : "border-white/[0.08] bg-white/[0.04]"
          )}>
            {plan.highlight && (
              <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-orange-600 to-amber-500 px-4 py-1 text-xs font-black text-white shadow-[0_8px_24px_rgba(234,88,12,0.3)]">
                Most Popular
              </div>
            )}
            <div className="text-xs font-black uppercase tracking-widest text-slate-400">{plan.name}</div>
            <div className="mt-4 flex items-end gap-1">
              <span className="text-5xl font-black text-white">{plan.price}</span>
              <span className="mb-1.5 text-sm text-slate-400">{plan.period}</span>
            </div>
            <div className="mt-1.5 text-xs font-medium text-slate-500">{plan.tagline}</div>

            <ul className="mt-8 space-y-3.5">
              {plan.features.map((f) => (
                <li key={f.label} className="flex items-center gap-3">
                  {f.included
                    ? <Check className="h-4 w-4 shrink-0 text-emerald-400" />
                    : <X className="h-4 w-4 shrink-0 text-slate-600" />}
                  <span className={cn("text-sm", f.included ? "text-slate-200" : "text-slate-600")}>{f.label}</span>
                </li>
              ))}
            </ul>

            <Link href="/register" className={cn(
              "mt-10 flex h-11 items-center justify-center rounded-xl text-sm font-black transition hover:-translate-y-0.5",
              plan.highlight
                ? "bg-gradient-to-r from-orange-600 to-amber-500 text-white shadow-[0_10px_28px_rgba(234,88,12,0.3)]"
                : "border border-white/10 bg-white/[0.05] text-white hover:bg-white/[0.1]"
            )}>
              {plan.cta}
            </Link>
          </motion.div>
        ))}
      </motion.div>

      {/* FAQ */}
      <div className="mx-auto mt-24 max-w-3xl">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} variants={stagger}>
          <motion.h2 variants={fadeUp} className="text-3xl font-black text-white">Frequently Asked Questions</motion.h2>
          <div className="mt-8 space-y-4">
            {faqs.map(([q, a]) => (
              <motion.div key={q} variants={fadeUp} className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-6">
                <div className="text-sm font-black text-white">{q}</div>
                <div className="mt-3 text-sm leading-7 text-slate-400">{a}</div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Bottom CTA */}
      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} className="mx-auto mt-20 max-w-2xl rounded-2xl border border-orange-300/20 bg-orange-500/[0.07] p-10 text-center">
        <h2 className="text-2xl font-black text-white">Still deciding?</h2>
        <p className="mt-3 text-sm leading-7 text-slate-400">Start with the free plan. No credit card, no lock-in. Upgrade when you are ready to scale.</p>
        <Link href="/register" className="mt-6 inline-flex h-11 items-center justify-center rounded-xl bg-gradient-to-r from-orange-600 to-amber-500 px-6 text-sm font-black text-white shadow-[0_10px_28px_rgba(234,88,12,0.28)] transition hover:-translate-y-0.5">
          Start for Free
        </Link>
      </motion.div>

      {/* Back link */}
      <div className="mt-10 text-center">
        <Link href="/" className="text-sm text-slate-500 transition hover:text-slate-300">← Back to home</Link>
      </div>
    </main>
  );
}
