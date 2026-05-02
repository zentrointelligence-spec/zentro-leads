"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Radar,
  Brain,
  Zap,
  Target,
  ArrowRight,
  Check,
  Menu,
  X,
  Sun,
  Moon,
  Flame,
  TrendingUp,
  Shield,
  Globe,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";
import { useTheme } from "./providers/theme-provider";

/* ── Animations ───────────────────────────────── */

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
};

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12 } },
};

/* ── Navbar ───────────────────────────────────── */

function Navbar() {
  const { theme, setTheme } = useTheme();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        scrolled
          ? "bg-background-primary/80 backdrop-blur-xl border-b border-border shadow-sm"
          : "bg-transparent"
      )}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary-dark shadow-glow">
            <Radar className="h-4.5 w-4.5 text-white" />
          </div>
          <span className="text-lg font-bold text-foreground-primary tracking-tight">
            LeadRadar
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8">
          <Link href="#features" className="text-sm font-medium text-foreground-secondary hover:text-foreground-primary transition-colors">
            Features
          </Link>
          <Link href="#pricing" className="text-sm font-medium text-foreground-secondary hover:text-foreground-primary transition-colors">
            Pricing
          </Link>
        </div>

        <div className="hidden md:flex items-center gap-3">
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="rounded-xl p-2 text-foreground-muted hover:bg-background-secondary hover:text-foreground-primary transition-colors"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          <Link href="/login" className="text-sm font-medium text-foreground-secondary hover:text-foreground-primary transition-colors">
            Login
          </Link>
          <Link href="/register">
            <Button>Get Started</Button>
          </Link>
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="rounded-xl p-2 text-foreground-secondary hover:bg-background-secondary md:hidden"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="border-t border-border bg-background-primary/95 backdrop-blur-xl px-4 py-4 md:hidden space-y-3">
          <Link href="#features" className="block text-sm font-medium text-foreground-secondary" onClick={() => setMobileOpen(false)}>
            Features
          </Link>
          <Link href="#pricing" className="block text-sm font-medium text-foreground-secondary" onClick={() => setMobileOpen(false)}>
            Pricing
          </Link>
          <div className="h-px bg-border" />
          <Link href="/login" className="block text-sm font-medium text-foreground-secondary" onClick={() => setMobileOpen(false)}>
            Login
          </Link>
          <Link href="/register" onClick={() => setMobileOpen(false)}>
            <Button className="w-full">Get Started</Button>
          </Link>
        </div>
      )}
    </nav>
  );
}

/* ── Hero ─────────────────────────────────────── */

function HeroSection() {
  return (
    <section className="relative overflow-hidden pt-36 pb-24 lg:pt-44 lg:pb-32">
      {/* Radial glow behind hero */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 h-[600px] w-[800px] bg-gradient-radial opacity-60 pointer-events-none" />

      <div className="relative mx-auto max-w-6xl px-4 text-center">
        <motion.div
          initial="hidden"
          animate="visible"
          variants={stagger}
          className="space-y-7"
        >
          <motion.div variants={fadeUp}>
            <span className="inline-flex items-center gap-2 rounded-full bg-hot-light px-4 py-1.5 text-xs font-semibold text-hot border border-hot/20">
              <Flame className="h-3.5 w-3.5" />
              9 HOT leads found today
            </span>
          </motion.div>

          <motion.h1
            variants={fadeUp}
            className="mx-auto max-w-3xl text-5xl font-extrabold tracking-tight text-foreground-primary lg:text-6xl"
          >
            Find Your Ideal Customers{" "}
            <span className="text-gradient">in Seconds</span>
          </motion.h1>

          <motion.p
            variants={fadeUp}
            className="mx-auto max-w-xl text-lg text-foreground-secondary leading-relaxed"
          >
            AI-powered lead generation with real buying intent signals. Stop
            guessing, start closing.
          </motion.p>

          <motion.div
            variants={fadeUp}
            className="flex flex-col sm:flex-row items-center justify-center gap-3"
          >
            <Link href="/register">
              <Button size="lg" leftIcon={<Zap className="h-4 w-4" />}>
                Start Free Trial
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="secondary" size="lg">
                Watch Demo
              </Button>
            </Link>
          </motion.div>

          <motion.div variants={fadeUp} className="flex items-center justify-center gap-6 pt-4 text-2xs text-foreground-muted">
            <span className="flex items-center gap-1.5">
              <Check className="h-3.5 w-3.5 text-success" /> No credit card
            </span>
            <span className="flex items-center gap-1.5">
              <Check className="h-3.5 w-3.5 text-success" /> 50 free leads
            </span>
            <span className="flex items-center gap-1.5">
              <Check className="h-3.5 w-3.5 text-success" /> Cancel anytime
            </span>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

/* ── Features ─────────────────────────────────── */

function FeaturesSection() {
  const features = [
    {
      icon: Brain,
      title: "AI ICP Builder",
      description:
        "Type one sentence. Get your perfect customer profile in seconds with AI-generated targeting criteria.",
    },
    {
      icon: Zap,
      title: "Intent Signals",
      description:
        "Know who's ready to buy RIGHT NOW based on real market signals like hiring, funding, and expansion.",
    },
    {
      icon: Target,
      title: "Lead Scoring",
      description:
        "Every lead scored 0-100 with a clear explanation of why they match your ideal customer profile.",
    },
  ];

  return (
    <section id="features" className="relative py-24 bg-background-secondary/50">
      <div className="mx-auto max-w-6xl px-4">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={stagger}
          className="grid gap-8 md:grid-cols-3"
        >
          {features.map((f) => (
            <motion.div
              key={f.title}
              variants={fadeUp}
              className="group rounded-2xl border border-card-border bg-card-bg p-7 shadow-sm card-hover"
            >
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary-light to-accent-light shadow-glow">
                <f.icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mb-2 text-lg font-bold text-foreground-primary">
                {f.title}
              </h3>
              <p className="text-sm text-foreground-secondary leading-relaxed">
                {f.description}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

/* ── How It Works ─────────────────────────────── */

function HowItWorksSection() {
  const steps = [
    {
      step: "01",
      title: "Describe your business",
      description:
        "Tell us what you sell and who you serve in one sentence. Our AI handles the rest.",
    },
    {
      step: "02",
      title: "AI finds matching companies",
      description:
        "We search thousands of companies, verify their details, and score each lead 0-100.",
    },
    {
      step: "03",
      title: "Contact hot leads instantly",
      description:
        "One-click outreach via WhatsApp, Email, or LinkedIn with AI-generated messages.",
    },
  ];

  return (
    <section className="relative py-24">
      <div className="mx-auto max-w-6xl px-4">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={stagger}
        >
          <motion.div variants={fadeUp} className="mb-14 text-center">
            <h2 className="text-3xl font-extrabold text-foreground-primary tracking-tight">
              How It Works
            </h2>
            <p className="mt-2 text-foreground-secondary">
              From idea to inbox in three simple steps
            </p>
          </motion.div>

          <div className="grid gap-10 md:grid-cols-3">
            {steps.map((s) => (
              <motion.div key={s.step} variants={fadeUp} className="text-center">
                <span className="text-5xl font-black text-gradient opacity-30">
                  {s.step}
                </span>
                <h3 className="mt-4 text-lg font-bold text-foreground-primary">
                  {s.title}
                </h3>
                <p className="mt-2 text-sm text-foreground-secondary leading-relaxed">
                  {s.description}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

/* ── Pricing ──────────────────────────────────── */

function PricingSection() {
  const plans = [
    {
      name: "Starter",
      price: "$29",
      leads: "500 leads/mo",
      features: [
        "AI ICP Builder",
        "Lead scoring",
        "Intent signals",
        "Email verification",
        "Basic outreach",
      ],
      cta: "Get Started",
      popular: false,
    },
    {
      name: "Growth",
      price: "$59",
      leads: "2,000 leads/mo",
      features: [
        "Everything in Starter",
        "WhatsApp outreach",
        "LinkedIn outreach",
        "ZIMS integration",
        "Priority support",
      ],
      cta: "Get Started",
      popular: true,
    },
    {
      name: "Pro",
      price: "$99",
      leads: "5,000 leads/mo",
      features: [
        "Everything in Growth",
        "Custom ICP tuning",
        "API access",
        "Team collaboration",
        "Dedicated account manager",
      ],
      cta: "Contact Sales",
      popular: false,
    },
  ];

  return (
    <section id="pricing" className="relative py-24 bg-background-secondary/50">
      <div className="mx-auto max-w-6xl px-4">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={stagger}
        >
          <motion.div variants={fadeUp} className="mb-14 text-center">
            <h2 className="text-3xl font-extrabold text-foreground-primary tracking-tight">
              Simple Pricing
            </h2>
            <p className="mt-2 text-foreground-secondary">
              Start free, upgrade when you grow
            </p>
          </motion.div>

          <div className="grid gap-8 md:grid-cols-3">
            {plans.map((plan) => (
              <motion.div
                key={plan.name}
                variants={fadeUp}
                className={cn(
                  "relative rounded-2xl border bg-card-bg p-7 shadow-sm transition-all duration-300",
                  plan.popular
                    ? "border-primary shadow-glow scale-[1.02]"
                    : "border-card-border hover:shadow-md"
                )}
              >
                {plan.popular && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-primary to-accent px-4 py-1 text-xs font-bold text-white shadow-glow">
                    Most Popular
                  </span>
                )}
                <h3 className="text-lg font-bold text-foreground-primary">
                  {plan.name}
                </h3>
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="text-4xl font-extrabold text-foreground-primary">
                    {plan.price}
                  </span>
                  <span className="text-sm text-foreground-muted">/month</span>
                </div>
                <p className="mt-1 text-sm text-foreground-secondary">
                  {plan.leads}
                </p>
                <ul className="mt-7 space-y-3">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2.5 text-sm text-foreground-secondary">
                      <Check className="h-4 w-4 text-success flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link href="/register" className="mt-7 block">
                  <Button
                    variant={plan.popular ? "primary" : "secondary"}
                    className="w-full"
                  >
                    {plan.cta}
                  </Button>
                </Link>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

/* ── Footer ───────────────────────────────────── */

function Footer() {
  return (
    <footer className="relative border-t border-border bg-background-primary py-14">
      <div className="mx-auto max-w-6xl px-4">
        <div className="flex flex-col md:flex-row items-center justify-between gap-5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary-dark">
              <Radar className="h-4 w-4 text-white" />
            </div>
            <span className="text-sm font-bold text-foreground-primary">
              LeadRadar
            </span>
          </div>
          <p className="text-xs text-foreground-muted">
            AI-powered lead generation for modern sales teams.
          </p>
          <p className="text-xs text-foreground-muted">
            &copy; 2025 LeadRadar. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}

/* ── Main Page ────────────────────────────────── */

export default function LandingPage() {
  const router = useRouter();

  useEffect(() => {
    fetch("/api/v1/auth/me", { credentials: "include" })
      .then((r) => {
        if (r.ok) router.push("/dashboard");
      })
      .catch(() => {});
  }, [router]);

  return (
    <div className="relative min-h-screen bg-background-primary overflow-hidden">
      <div className="relative z-10">
        <Navbar />
        <HeroSection />
        <FeaturesSection />
        <HowItWorksSection />
        <PricingSection />
        <Footer />
      </div>
    </div>
  );
}
