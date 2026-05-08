"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  ArrowUpRight,
  CheckCircle2,
  XCircle,
  ToggleLeft,
  ToggleRight,
  Zap,
  Shield,
  User,
  Bell,
  CreditCard,
  Moon,
  Sun,
  Monitor,
  Loader2,
  KeyRound,
  Link2,
  Link2Off,
  ExternalLink,
  Save,
  RefreshCcw,
  Star,
  Rocket,
  Building2,
  Landmark,
  Phone,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/cn";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useTheme } from "@/app/providers/theme-provider";

interface UserData {
  id: string;
  email: string;
  full_name: string;
  company_name: string | null;
  phone: string | null;
  plan: string;
  leads_used_this_month: number;
  leads_limit: number;
}

interface ZimsIntegration {
  zims_linked: boolean;
  zims_api_url: string | null;
  zims_api_key_masked: string | null;
  zims_agency_id: string | null;
  zims_agent_id: string | null;
  zims_last_sync_at: string | null;
  zims_leads_pushed: number;
  leads_pushed_this_month: number;
}

type SettingsTab = "general" | "integrations" | "preferences" | "billing";

const PLAN_LIMITS: Record<string, number> = {
  free: 25,
  starter: 500,
  growth: 2000,
  pro: 5000,
  agency: 20000,
};

const ZIMS_WEB_LOGIN_URL =
  process.env.NEXT_PUBLIC_ZIMS_WEB_URL ?? "http://localhost:3000/login";

function ToggleRow({
  label,
  description,
  enabled,
  onChange,
}: {
  label: string;
  description?: string;
  enabled: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!enabled)}
      className="flex w-full items-center justify-between rounded-lg border border-border bg-card-bg px-4 py-3 transition hover:border-primary/20 hover:shadow-sm"
    >
      <div className="text-left">
        <span className="text-sm font-medium text-foreground-primary">
          {label}
        </span>
        {description && (
          <p className="text-2xs text-foreground-muted mt-0.5">{description}</p>
        )}
      </div>
      {enabled ? (
        <ToggleRight className="h-6 w-6 text-primary flex-shrink-0" />
      ) : (
        <ToggleLeft className="h-6 w-6 text-foreground-muted flex-shrink-0" />
      )}
    </button>
  );
}

function SettingsSection({
  title,
  description,
  icon,
  children,
}: {
  title: string;
  description: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-start gap-4 mb-5">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-primary-light">
            {icon}
          </div>
          <div>
            <h3 className="text-base font-bold text-foreground-primary">
              {title}
            </h3>
            <p className="text-sm text-foreground-muted">{description}</p>
          </div>
        </div>
        <div className="space-y-3">{children}</div>
      </CardContent>
    </Card>
  );
}

const TABS: { key: SettingsTab; label: string; icon: React.ElementType }[] = [
  { key: "general", label: "General", icon: User },
  { key: "integrations", label: "Integrations", icon: ArrowUpRight },
  { key: "preferences", label: "Preferences", icon: Zap },
  { key: "billing", label: "Billing", icon: CreditCard },
];

function ThemeOption({
  label,
  icon: Icon,
  selected,
  onSelect,
}: {
  value: string;
  label: string;
  icon: React.ElementType;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex flex-col items-center gap-2 rounded-lg border px-4 py-3 transition-all",
        selected
          ? "border-primary bg-primary-light text-primary"
          : "border-border bg-card-bg text-foreground-secondary hover:border-primary/30"
      )}
    >
      <Icon className="h-5 w-5" />
      <span className="text-xs font-medium">{label}</span>
    </button>
  );
}

// ── Billing plan definitions ──────────────────────────────────────────────────

const PLAN_ORDER = ["free", "starter", "growth", "pro", "agency"] as const;
type PlanKey = (typeof PLAN_ORDER)[number];

interface PlanDef {
  key: PlanKey;
  name: string;
  price: string;
  period: string;
  leads: string;
  description: string;
  features: string[];
  icon: React.ElementType;
  highlight: boolean;
}

const PLANS: PlanDef[] = [
  {
    key: "starter",
    name: "Starter",
    price: "$19",
    period: "/mo",
    leads: "750 leads / month",
    description: "Perfect for solo agents just getting started.",
    features: [
      "750 leads per month",
      "AI ICP builder",
      "Email verification",
      "WhatsApp outreach copy",
      "CSV export",
    ],
    icon: Star,
    highlight: false,
  },
  {
    key: "growth",
    name: "Growth",
    price: "$49",
    period: "/mo",
    leads: "3,000 leads / month",
    description: "Best for growing agencies scaling their pipeline.",
    features: [
      "3,000 leads per month",
      "Everything in Starter",
      "Intent signals & news alerts",
      "ZIMS auto-push",
      "Priority scraping queue",
    ],
    icon: Rocket,
    highlight: true,
  },
  {
    key: "pro",
    name: "Pro",
    price: "$99",
    period: "/mo",
    leads: "10,000 leads / month",
    description: "For high-volume teams who need serious data.",
    features: [
      "10,000 leads per month",
      "Everything in Growth",
      "Team seats (coming soon)",
      "Dedicated scraping nodes",
      "Advanced analytics",
    ],
    icon: Building2,
    highlight: false,
  },
];

function planRank(plan: string): number {
  return PLAN_ORDER.indexOf(plan as PlanKey);
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<SettingsTab>(() => {
    const tab = searchParams.get("tab");
    if (tab === "billing" || tab === "integrations" || tab === "preferences" || tab === "general") {
      return tab as SettingsTab;
    }
    return "general";
  });
  const { theme, setTheme } = useTheme();

  /* Checkout state */
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const billingToastFired = useRef(false);

  /* Payment method selection */
  type PaymentMethod = "card" | "fpx" | "upi";
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("card");
  const [fpxPhone, setFpxPhone] = useState("");
  const [fpxLoading, setFpxLoading] = useState<string | null>(null);
  const [upiLoading, setUpiLoading] = useState<string | null>(null);

  /* User data */
  const [user, setUser] = useState<UserData | null>(null);
  const [userLoading, setUserLoading] = useState(true);

  /* Profile form */
  const [profileForm, setProfileForm] = useState({
    full_name: "",
    company_name: "",
    phone: "",
  });
  const [profileSaving, setProfileSaving] = useState(false);

  /* Toggles */
  const [autoPushZims, setAutoPushZims] = useState(false);
  const [emailNotifs, setEmailNotifs] = useState(true);
  const [showConfidence, setShowConfidence] = useState(true);
  const [showWhyNow, setShowWhyNow] = useState(true);
  const [enableDragDrop, setEnableDragDrop] = useState(true);

  /* ZIMS integration */
  const [zimsIntegration, setZimsIntegration] = useState<ZimsIntegration | null>(null);
  const [zimsLoading, setZimsLoading] = useState(false);
  const [zimsForm, setZimsForm] = useState({ url: "", key: "", agencyId: "", agentId: "" });
  const [zimsSaving, setZimsSaving] = useState(false);
  const [zimsTesting, setZimsTesting] = useState(false);
  const [zimsTestResult, setZimsTestResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    async function fetchUser() {
      try {
        const res = await fetch("/api/v1/auth/me", { credentials: "include" });
        if (res.ok) {
          const data = await res.json();
          setUser(data);
          setProfileForm({
            full_name: data.full_name ?? "",
            company_name: data.company_name ?? "",
            phone: data.phone ?? "",
          });
        }
      } catch {
        toast.error("Failed to load profile");
      } finally {
        setUserLoading(false);
      }
    }
    fetchUser();
  }, []);

  async function fetchZimsIntegration() {
    setZimsLoading(true);
    try {
      const res = await fetch("/api/v1/settings/integrations", { credentials: "include" });
      if (res.ok) {
        const data: ZimsIntegration = await res.json();
        setZimsIntegration(data);
        setZimsForm({
          url: data.zims_api_url ?? "",
          key: "",
          agencyId: data.zims_agency_id ?? "",
          agentId: data.zims_agent_id ?? "",
        });
        setAutoPushZims(data.zims_linked);
      }
    } catch {
      /* non-blocking */
    } finally {
      setZimsLoading(false);
    }
  }

  useEffect(() => {
    if (activeTab === "integrations") {
      fetchZimsIntegration();
    }
  }, [activeTab]);

  /* Show success/cancelled toast after Stripe redirect — fires once per page load */
  useEffect(() => {
    if (billingToastFired.current) return;
    const billingStatus = searchParams.get("billing");
    const plan = searchParams.get("plan");
    if (billingStatus === "success") {
      billingToastFired.current = true;
      toast.success(
        plan
          ? `You're now on the ${plan.charAt(0).toUpperCase() + plan.slice(1)} plan!`
          : "Subscription activated!",
        { description: "Your lead limit has been updated. Enjoy Zentro Leads." }
      );
      router.replace("/dashboard/settings?tab=billing");
    } else if (billingStatus === "cancelled") {
      billingToastFired.current = true;
      toast("Checkout cancelled", { description: "No charge was made." });
      router.replace("/dashboard/settings?tab=billing");
    } else if (billingStatus === "failed") {
      billingToastFired.current = true;
      toast.error("FPX payment unsuccessful", {
        description: "Your bank declined the transaction. No charge was made.",
      });
      router.replace("/dashboard/settings?tab=billing");
    }
  }, [searchParams, router]);

  function handleAutoPushChange(value: boolean) {
    setAutoPushZims(value);
  }

  async function handleCheckout(plan: string) {
    setCheckoutLoading(plan);
    try {
      const res = await fetch("/api/v1/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ plan }),
      });
      const data = await res.json();
      if (!res.ok) {
        toast.error(data.detail ?? "Could not start checkout");
        return;
      }
      window.location.href = data.checkout_url;
    } catch {
      toast.error("Failed to connect to billing. Please try again.");
    } finally {
      setCheckoutLoading(null);
    }
  }

  async function handleFpxCheckout(plan: string) {
    if (!fpxPhone.trim()) {
      toast.error("Please enter your Malaysian mobile number for FPX.");
      return;
    }
    setFpxLoading(plan);
    try {
      const res = await fetch("/api/v1/billing/checkout/fpx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ plan, phone: fpxPhone.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        toast.error(data.detail ?? "Could not start FPX payment");
        return;
      }
      window.location.href = data.fpx_url;
    } catch {
      toast.error("Failed to connect to FPX payment. Please try again.");
    } finally {
      setFpxLoading(null);
    }
  }

  async function handleUpiCheckout(plan: string) {
    setUpiLoading(plan);
    try {
      // Step 1 — Create Razorpay order on backend
      const res = await fetch("/api/v1/billing/checkout/upi", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ plan }),
      });
      const order = await res.json();
      if (!res.ok) {
        toast.error(order.detail ?? "Could not create payment order");
        return;
      }

      // Step 2 — Load Razorpay.js script dynamically (idempotent)
      await new Promise<void>((resolve, reject) => {
        if (document.querySelector('script[src*="checkout.razorpay.com"]')) {
          resolve();
          return;
        }
        const script = document.createElement("script");
        script.src = "https://checkout.razorpay.com/v1/checkout.js";
        script.onload = () => resolve();
        script.onerror = () => reject(new Error("Failed to load Razorpay.js"));
        document.head.appendChild(script);
      });

      // Step 3 — Open Razorpay modal
      const rzp = new (window as unknown as {
        Razorpay: new (opts: {
          key: string;
          order_id: string;
          amount: number;
          currency: string;
          name: string;
          description: string;
          prefill: { name: string; email: string; };
          theme: { color: string; };
          handler: (resp: {
            razorpay_payment_id: string;
            razorpay_order_id: string;
            razorpay_signature: string;
          }) => void;
          modal: { ondismiss: () => void; };
        }) => { open(): void };
      }).Razorpay({
        key:         order.razorpay_key,
        order_id:    order.order_id,
        amount:      order.amount,
        currency:    order.currency,
        name:        "Zentro Leads",
        description: `${plan.charAt(0).toUpperCase() + plan.slice(1)} Plan`,
        prefill: {
          name:  user?.full_name  ?? "",
          email: user?.email      ?? "",
        },
        theme: { color: "#6366f1" },
        handler: async (paymentResponse) => {
          // Step 4 — Verify signature on backend, activate plan
          try {
            const verifyRes = await fetch("/api/v1/billing/razorpay/verify", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "include",
              body: JSON.stringify({
                order_id:   paymentResponse.razorpay_order_id,
                payment_id: paymentResponse.razorpay_payment_id,
                signature:  paymentResponse.razorpay_signature,
                plan,
              }),
            });
            const result = await verifyRes.json();
            if (verifyRes.ok && result.success) {
              toast.success(
                `You're now on the ${plan.charAt(0).toUpperCase() + plan.slice(1)} plan!`,
                { description: "Your lead limit has been updated. Enjoy Zentro Leads." }
              );
              // Refresh user data to show updated plan
              const meRes = await fetch("/api/v1/auth/me", { credentials: "include" });
              if (meRes.ok) setUser(await meRes.json());
            } else {
              toast.error(result.detail ?? "Payment received but could not activate plan. Contact support.");
            }
          } catch {
            toast.error("Could not verify payment. Contact support with your payment ID.");
          }
        },
        modal: {
          ondismiss: () => {
            toast("Payment cancelled", { description: "No charge was made." });
            setUpiLoading(null);
          },
        },
      });

      rzp.open();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      toast.error(`UPI payment failed: ${message}`);
    } finally {
      setUpiLoading(null);
    }
  }

  async function handleSaveProfile() {
    setProfileSaving(true);
    try {
      const res = await fetch("/api/v1/auth/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(profileForm),
      });
      if (res.ok) {
        toast.success("Profile updated");
        const updated = await res.json();
        setUser(updated);
      } else {
        const err = await res.json().catch(() => ({ detail: "Update failed" }));
        toast.error(err.detail);
      }
    } catch {
      toast.error("Failed to update profile");
    } finally {
      setProfileSaving(false);
    }
  }

  async function handleSaveZims() {
    if (!zimsForm.url.trim()) {
      toast.error("Enter your ZIMS URL first");
      return;
    }
    if (!zimsForm.key.trim()) {
      toast.error("Enter your ZIMS API key first");
      return;
    }
    setZimsSaving(true);
    try {
      const res = await fetch("/api/v1/settings/integrations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          zims_api_url: zimsForm.url.trim(),
          zims_api_key: zimsForm.key.trim(),
          zims_agency_id: zimsForm.agencyId.trim() || null,
          zims_agent_id: zimsForm.agentId.trim() || null,
        }),
      });
      if (res.ok) {
        const data: ZimsIntegration = await res.json();
        setZimsIntegration(data);
        setZimsForm((f) => ({ ...f, key: "" }));
        setZimsTestResult(null);
        toast.success("ZIMS config saved");
      } else {
        const err = await res.json().catch(() => ({ detail: "Save failed" }));
        toast.error(err.detail ?? "Save failed");
      }
    } catch {
      toast.error("Failed to save ZIMS config");
    } finally {
      setZimsSaving(false);
    }
  }

  async function handleTestZims() {
    setZimsTesting(true);
    setZimsTestResult(null);
    try {
      const res = await fetch("/api/v1/settings/integrations/test", {
        method: "POST",
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setZimsTestResult({ success: data.success, message: data.message });
        if (data.success) {
          toast.success("ZIMS connection verified");
          fetchZimsIntegration();
        } else {
          toast.error(data.message);
        }
      } else {
        setZimsTestResult({ success: false, message: "Test request failed" });
        toast.error("Test request failed");
      }
    } catch {
      setZimsTestResult({ success: false, message: "Network error" });
      toast.error("Network error during test");
    } finally {
      setZimsTesting(false);
    }
  }

  const planLimit = PLAN_LIMITS[user?.plan ?? "free"] ?? 25;
  const usedPct = Math.round(
    ((user?.leads_used_this_month ?? 0) / Math.max(planLimit, 1)) * 100
  );

  return (
    <div className="mx-auto max-w-3xl space-y-6 animate-fade-in-up">
      <div>
        <h1 className="text-2xl font-bold text-foreground-primary">Settings</h1>
        <p className="mt-0.5 text-sm text-foreground-secondary">
          Manage your pipeline preferences, integrations, and account
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 rounded-xl border border-border bg-background-secondary p-1">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition-colors whitespace-nowrap",
              activeTab === tab.key
                ? "bg-card-bg text-foreground-primary shadow-sm"
                : "text-foreground-muted hover:text-foreground-secondary"
            )}
          >
            <tab.icon className="h-3.5 w-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* General */}
      {activeTab === "general" && (
        <div className="space-y-4">
          <SettingsSection
            title="Profile"
            description="Your account information"
            icon={<User className="h-5 w-5 text-primary" />}
          >
            {userLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 text-primary animate-spin" />
              </div>
            ) : (
              <>
                <Input
                  label="Full Name"
                  value={profileForm.full_name}
                  onChange={(e) =>
                    setProfileForm((f) => ({ ...f, full_name: e.target.value }))
                  }
                />
                <Input
                  label="Email"
                  type="email"
                  value={user?.email ?? ""}
                  disabled
                  icon={<span className="text-foreground-muted text-xs">@</span>}
                />
                <Input
                  label="Company Name"
                  value={profileForm.company_name}
                  onChange={(e) =>
                    setProfileForm((f) => ({
                      ...f,
                      company_name: e.target.value,
                    }))
                  }
                />
                <Input
                  label="Phone"
                  type="tel"
                  value={profileForm.phone}
                  onChange={(e) =>
                    setProfileForm((f) => ({ ...f, phone: e.target.value }))
                  }
                />
                <Button
                  onClick={handleSaveProfile}
                  isLoading={profileSaving}
                  leftIcon={<Save className="h-4 w-4" />}
                >
                  Save Profile
                </Button>
              </>
            )}
          </SettingsSection>

          <SettingsSection
            title="Account Security"
            description="Your session and security status"
            icon={<Shield className="h-5 w-5 text-primary" />}
          >
            <div className="flex items-center gap-2 rounded-lg bg-success-light px-3 py-2 border border-success/20">
              <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-success" />
              <span className="text-xs text-success font-medium">
                Session is active and secure
              </span>
            </div>
            <p className="text-2xs text-foreground-muted">
              Sign out from the sidebar if you need to switch accounts.
            </p>
          </SettingsSection>

          <SettingsSection
            title="Appearance"
            description="Choose your preferred theme"
            icon={<Moon className="h-5 w-5 text-primary" />}
          >
            <div className="grid grid-cols-3 gap-3">
              <ThemeOption
                value="light"
                label="Light"
                icon={Sun}
                selected={theme === "light"}
                onSelect={() => setTheme("light")}
              />
              <ThemeOption
                value="dark"
                label="Dark"
                icon={Moon}
                selected={theme === "dark"}
                onSelect={() => setTheme("dark")}
              />
              <ThemeOption
                value="system"
                label="System"
                icon={Monitor}
                selected={theme === "system"}
                onSelect={() => {
                  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
                  setTheme(prefersDark ? "dark" : "light");
                }}
              />
            </div>
          </SettingsSection>
        </div>
      )}

      {/* Integrations */}
      {activeTab === "integrations" && (
        <div className="space-y-4">
          <SettingsSection
            title="ZIMS Integration"
            description="Optional — connect ZIMS if you use both products. Standalone users can skip this entirely."
            icon={<Link2 className="h-5 w-5 text-primary" />}
          >
            {zimsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 text-primary animate-spin" />
              </div>
            ) : (
              <>
                {/* Status banner */}
                {zimsIntegration?.zims_linked ? (
                  <div className="flex items-center justify-between rounded-lg border border-success/20 bg-success-light px-4 py-3">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-success flex-shrink-0" />
                      <div>
                        <p className="text-sm font-semibold text-success">Connected to ZIMS</p>
                        <p className="text-2xs text-foreground-muted mt-0.5">
                          {zimsIntegration.zims_api_url}
                        </p>
                      </div>
                    </div>
                    <a
                      href={ZIMS_WEB_LOGIN_URL}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 rounded-md border border-success/30 bg-white/10 px-3 py-1.5 text-xs font-medium text-success hover:bg-success/10 transition-colors"
                    >
                      Open ZIMS
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 rounded-lg border border-border bg-background-secondary px-4 py-3">
                    <Link2Off className="h-4 w-4 text-foreground-muted flex-shrink-0" />
                    <p className="text-sm text-foreground-secondary">Not connected — enter your ZIMS details below</p>
                  </div>
                )}

                {/* Stats row */}
                {zimsIntegration?.zims_linked && (
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg border border-border bg-background-secondary px-4 py-3">
                      <p className="text-2xs text-foreground-muted">Leads pushed (this month)</p>
                      <p className="mt-1 text-xl font-bold text-foreground-primary">
                        {zimsIntegration.leads_pushed_this_month}
                      </p>
                    </div>
                    <div className="rounded-lg border border-border bg-background-secondary px-4 py-3">
                      <p className="text-2xs text-foreground-muted">Total leads pushed</p>
                      <p className="mt-1 text-xl font-bold text-foreground-primary">
                        {zimsIntegration.zims_leads_pushed}
                      </p>
                    </div>
                  </div>
                )}

                {zimsIntegration?.zims_last_sync_at && (
                  <p className="text-2xs text-foreground-muted">
                    Last sync:{" "}
                    {new Date(zimsIntegration.zims_last_sync_at).toLocaleString("en-MY", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </p>
                )}

                {/* Form */}
                <div className="space-y-3 pt-1">
                  <div>
                    <label className="block text-xs font-medium text-foreground-secondary mb-1.5">
                      ZIMS Instance URL
                    </label>
                    <div className="relative">
                      <ArrowUpRight className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground-muted" />
                      <input
                        type="url"
                        value={zimsForm.url}
                        onChange={(e) => setZimsForm((f) => ({ ...f, url: e.target.value }))}
                        placeholder="https://app.zims.io"
                        className="w-full h-10 rounded-md border border-border bg-background-elevated pl-9 pr-3 text-sm text-foreground-primary placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-foreground-secondary mb-1.5">
                      ZIMS Internal API Key
                      {zimsIntegration?.zims_api_key_masked && (
                        <span className="ml-2 font-mono text-foreground-muted">
                          (current: {zimsIntegration.zims_api_key_masked})
                        </span>
                      )}
                    </label>
                    <div className="relative">
                      <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground-muted" />
                      <input
                        type="password"
                        value={zimsForm.key}
                        onChange={(e) => setZimsForm((f) => ({ ...f, key: e.target.value }))}
                        placeholder={zimsIntegration?.zims_api_key_masked ? "Enter new key to replace…" : "Paste your ZIMS internal API key"}
                        className="w-full h-10 rounded-md border border-border bg-background-elevated pl-9 pr-3 text-sm text-foreground-primary placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-foreground-secondary mb-1.5">
                      ZIMS Agency ID
                      <span className="ml-1.5 text-foreground-muted font-normal">(optional — for local/shared tenant routing)</span>
                    </label>
                    <div className="relative">
                      <Shield className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground-muted" />
                      <input
                        type="number"
                        min="1"
                        inputMode="numeric"
                        value={zimsForm.agencyId}
                        onChange={(e) => setZimsForm((f) => ({ ...f, agencyId: e.target.value }))}
                        placeholder="Example: 5"
                        className="w-full h-10 rounded-md border border-border bg-background-elevated pl-9 pr-3 text-sm text-foreground-primary placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>
                    <p className="mt-1.5 text-2xs text-foreground-muted">
                      Hot leads from this LeadRadar subscription will be imported into this exact ZIMS agency.
                    </p>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-foreground-secondary mb-1.5">
                      ZIMS Agent ID
                      <span className="ml-1.5 text-foreground-muted font-normal">(optional — for shared agency accounts)</span>
                    </label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground-muted" />
                      <input
                        type="text"
                        value={zimsForm.agentId}
                        onChange={(e) => setZimsForm((f) => ({ ...f, agentId: e.target.value }))}
                        placeholder="Example: 5 or agent_abc123"
                        className="w-full h-10 rounded-md border border-border bg-background-elevated pl-9 pr-3 text-sm text-foreground-primary placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>
                    <p className="mt-1.5 text-2xs text-foreground-muted">
                      Solo agents can leave this blank. Shared ZIMS agencies should paste the ZIMS agent/user ID for assignment.
                    </p>
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <Button
                      onClick={handleSaveZims}
                      isLoading={zimsSaving}
                      leftIcon={<Save className="h-4 w-4" />}
                    >
                      Save Config
                    </Button>
                    {zimsIntegration?.zims_linked && (
                      <Button
                        variant="secondary"
                        onClick={handleTestZims}
                        isLoading={zimsTesting}
                        leftIcon={<RefreshCcw className="h-4 w-4" />}
                      >
                        Test Connection
                      </Button>
                    )}
                  </div>

                  {zimsTestResult && (
                    <div
                      className={cn(
                        "flex items-center gap-2 rounded-md px-3 py-2 text-xs font-medium",
                        zimsTestResult.success
                          ? "bg-success-light border border-success/20 text-success"
                          : "bg-hot/10 border border-hot/20 text-hot"
                      )}
                    >
                      {zimsTestResult.success ? (
                        <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0" />
                      ) : (
                        <XCircle className="h-3.5 w-3.5 flex-shrink-0" />
                      )}
                      {zimsTestResult.message}
                    </div>
                  )}
                </div>

                <ToggleRow
                  label="Auto-push HOT leads to ZIMS"
                  description="Any lead scoring ≥ 85 will automatically sync to ZIMS in the background"
                  enabled={autoPushZims}
                  onChange={handleAutoPushChange}
                />
              </>
            )}
          </SettingsSection>
        </div>
      )}

      {/* Preferences */}
      {activeTab === "preferences" && (
        <div className="space-y-4">
          <SettingsSection
            title="Pipeline Preferences"
            description="Customize how leads appear in your dashboard"
            icon={<Zap className="h-5 w-5 text-primary" />}
          >
            <ToggleRow
              label="Show email confidence on cards"
              description="Display confidence percentage next to email addresses"
              enabled={showConfidence}
              onChange={setShowConfidence}
            />
            <ToggleRow
              label="Show WHY NOW preview"
              description="Display intent signal summaries on lead cards"
              enabled={showWhyNow}
              onChange={setShowWhyNow}
            />
            <ToggleRow
              label="Enable drag & drop"
              description="Move leads between pipeline stages via drag and drop"
              enabled={enableDragDrop}
              onChange={setEnableDragDrop}
            />
          </SettingsSection>

          <SettingsSection
            title="Notifications"
            description="Choose what you want to be notified about"
            icon={<Bell className="h-5 w-5 text-primary" />}
          >
            <ToggleRow
              label="Email notifications"
              description="Receive daily summaries and alerts via email"
              enabled={emailNotifs}
              onChange={setEmailNotifs}
            />
          </SettingsSection>
        </div>
      )}

      {/* Billing */}
      {activeTab === "billing" && (
        <div className="space-y-4">
          {/* Current plan + usage */}
          <SettingsSection
            title="Plan & Usage"
            description="Your current subscription and monthly lead usage"
            icon={<CreditCard className="h-5 w-5 text-primary" />}
          >
            {userLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 text-primary animate-spin" />
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between rounded-lg border border-primary/20 bg-primary/5 px-4 py-3">
                  <div>
                    <p className="text-sm font-bold text-foreground-primary capitalize">
                      {user?.plan ?? "free"} Plan
                    </p>
                    <p className="text-2xs text-foreground-muted mt-0.5">
                      {planLimit.toLocaleString()} leads / month
                    </p>
                  </div>
                  <Badge variant="secondary">Current Plan</Badge>
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-foreground-secondary">Leads used this month</span>
                    <span className="font-semibold text-foreground-primary">
                      {(user?.leads_used_this_month ?? 0).toLocaleString()} / {planLimit.toLocaleString()}
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-border overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        usedPct >= 90 ? "bg-red-500" : usedPct >= 70 ? "bg-amber-500" : "bg-primary"
                      )}
                      style={{ width: `${Math.min(usedPct, 100)}%` }}
                    />
                  </div>
                  {usedPct >= 80 && (
                    <p className="text-2xs text-amber-500 font-medium">
                      You&apos;ve used {usedPct}% of your monthly limit. Upgrade to avoid hitting the cap.
                    </p>
                  )}
                </div>
              </>
            )}
          </SettingsSection>

          {/* Plan cards */}
          <div>
            <p className="text-sm font-semibold text-foreground-primary mb-3">Choose a plan</p>
            <div className="grid gap-4 sm:grid-cols-3">
              {PLANS.map((plan) => {
                const currentRank  = planRank(user?.plan ?? "free");
                const planRankVal  = planRank(plan.key);
                const isCurrent    = (user?.plan ?? "free") === plan.key;
                const isUpgrade    = planRankVal > currentRank;
                const isCardLoading = checkoutLoading === plan.key;
                const isFpxLoading  = fpxLoading === plan.key;
                const isUpiLoading  = upiLoading === plan.key;
                const isLoading     = isCardLoading || isFpxLoading || isUpiLoading;
                const PlanIcon     = plan.icon;

                return (
                  <div
                    key={plan.key}
                    className={cn(
                      "relative flex flex-col rounded-xl border p-5 transition-shadow",
                      plan.highlight
                        ? "border-primary bg-primary/5 shadow-md shadow-primary/10"
                        : "border-border bg-card-bg",
                      isCurrent && "ring-2 ring-primary"
                    )}
                  >
                    {plan.highlight && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                        <span className="inline-flex items-center gap-1 rounded-full bg-primary px-2.5 py-0.5 text-[10px] font-bold text-white shadow">
                          Most Popular
                        </span>
                      </div>
                    )}

                    <div className="flex items-center gap-2 mb-3">
                      <div className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-lg",
                        plan.highlight ? "bg-primary/15" : "bg-background-secondary"
                      )}>
                        <PlanIcon className={cn("h-4 w-4", plan.highlight ? "text-primary" : "text-foreground-secondary")} />
                      </div>
                      <div>
                        <p className="text-sm font-bold text-foreground-primary">{plan.name}</p>
                        <p className="text-2xs text-foreground-muted">{plan.leads}</p>
                      </div>
                    </div>

                    <div className="mb-3">
                      <span className="text-2xl font-extrabold text-foreground-primary">{plan.price}</span>
                      <span className="text-xs text-foreground-muted">{plan.period}</span>
                    </div>

                    <p className="text-2xs text-foreground-secondary mb-3">{plan.description}</p>

                    <ul className="space-y-1.5 mb-4 flex-1">
                      {plan.features.map((f) => (
                        <li key={f} className="flex items-start gap-1.5 text-xs text-foreground-secondary">
                          <CheckCircle2 className="h-3.5 w-3.5 text-primary flex-shrink-0 mt-0.5" />
                          {f}
                        </li>
                      ))}
                    </ul>

                    {isCurrent ? (
                      <div className="rounded-lg border border-primary/20 bg-primary/10 px-3 py-2 text-center text-xs font-semibold text-primary">
                        Current Plan
                      </div>
                    ) : isUpgrade ? (
                      <button
                        type="button"
                        disabled={isLoading}
                        onClick={() =>
                          paymentMethod === "fpx"
                            ? handleFpxCheckout(plan.key)
                            : paymentMethod === "upi"
                              ? handleUpiCheckout(plan.key)
                              : handleCheckout(plan.key)
                        }
                        className={cn(
                          "flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-bold transition-colors disabled:opacity-60",
                          plan.highlight
                            ? "bg-primary text-white hover:bg-primary/90"
                            : "border border-primary/30 bg-primary-light text-primary hover:bg-primary/10"
                        )}
                      >
                        {isLoading ? (
                          <>
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            {paymentMethod === "upi" ? "Opening…" : "Redirecting…"}
                          </>
                        ) : (
                          <>
                            {paymentMethod === "fpx"
                              ? <Landmark className="h-3.5 w-3.5" />
                              : paymentMethod === "upi"
                                ? <Phone className="h-3.5 w-3.5" />
                                : <Rocket className="h-3.5 w-3.5" />
                            }
                            Upgrade to {plan.name}
                          </>
                        )}
                      </button>
                    ) : (
                      <div className="rounded-lg border border-border px-3 py-2 text-center text-xs text-foreground-muted">
                        Lower than current plan
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Agency CTA */}
            <div className="mt-4 rounded-xl border border-border bg-background-secondary px-5 py-4 flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-bold text-foreground-primary">Agency Plan — $199/mo</p>
                <p className="text-xs text-foreground-muted mt-0.5">
                  Unlimited leads · Multi-seat · Dedicated support · White-label ready
                </p>
              </div>
              {(user?.plan ?? "free") === "agency" ? (
                <Badge variant="secondary">Current Plan</Badge>
              ) : (
                <button
                  type="button"
                  disabled={checkoutLoading === "agency" || fpxLoading === "agency" || upiLoading === "agency"}
                  onClick={() =>
                    paymentMethod === "fpx"
                      ? handleFpxCheckout("agency")
                      : paymentMethod === "upi"
                        ? handleUpiCheckout("agency")
                        : handleCheckout("agency")
                  }
                  className="flex-shrink-0 flex items-center gap-1.5 rounded-lg border border-border bg-card-bg px-4 py-2 text-xs font-semibold text-foreground-primary hover:border-primary/30 transition-colors disabled:opacity-60"
                >
                  {checkoutLoading === "agency" || fpxLoading === "agency" || upiLoading === "agency" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : paymentMethod === "fpx" ? (
                    <Landmark className="h-3.5 w-3.5" />
                  ) : paymentMethod === "upi" ? (
                    <Phone className="h-3.5 w-3.5" />
                  ) : (
                    <Rocket className="h-3.5 w-3.5" />
                  )}
                  Upgrade to Agency
                </button>
              )}
            </div>

            {/* ── Payment method selector ─────────────────────────────── */}
            <div className="mt-5 rounded-xl border border-border bg-background-secondary p-4">
              <p className="text-xs font-semibold text-foreground-primary mb-3">
                Payment Method
              </p>
              <div className="grid grid-cols-2 gap-2">
                {/* Card */}
                <button
                  type="button"
                  onClick={() => setPaymentMethod("card")}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg border px-4 py-3 text-xs font-medium transition-all",
                    paymentMethod === "card"
                      ? "border-primary bg-primary/5 text-primary"
                      : "border-border bg-card-bg text-foreground-secondary hover:border-primary/30"
                  )}
                >
                  <CreditCard className="h-4 w-4 flex-shrink-0" />
                  <div className="text-left">
                    <p className="font-semibold">Credit / Debit Card</p>
                    <p className="text-[10px] text-foreground-muted font-normal">Visa, Mastercard via Stripe</p>
                  </div>
                </button>

                {/* FPX */}
                <button
                  type="button"
                  onClick={() => setPaymentMethod("fpx")}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg border px-4 py-3 text-xs font-medium transition-all",
                    paymentMethod === "fpx"
                      ? "border-primary bg-primary/5 text-primary"
                      : "border-border bg-card-bg text-foreground-secondary hover:border-primary/30"
                  )}
                >
                  <Landmark className="h-4 w-4 flex-shrink-0" />
                  <div className="text-left">
                    <p className="font-semibold">FPX Online Banking</p>
                    <p className="text-[10px] text-foreground-muted font-normal">Malaysian banks via Billplz</p>
                  </div>
                </button>

                {/* UPI */}
                <button
                  type="button"
                  onClick={() => setPaymentMethod("upi")}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg border px-4 py-3 text-xs font-medium transition-all",
                    paymentMethod === "upi"
                      ? "border-primary bg-primary/5 text-primary"
                      : "border-border bg-card-bg text-foreground-secondary hover:border-primary/30"
                  )}
                >
                  <Phone className="h-4 w-4 flex-shrink-0" />
                  <div className="text-left">
                    <p className="font-semibold">UPI / NetBanking</p>
                    <p className="text-[10px] text-foreground-muted font-normal">India — UPI, cards via Razorpay</p>
                  </div>
                </button>
              </div>

              {/* FPX phone input — shown only when FPX is selected */}
              {paymentMethod === "fpx" && (
                <div className="mt-3">
                  <label className="block text-xs font-medium text-foreground-secondary mb-1.5">
                    Malaysian Mobile Number
                    <span className="ml-1.5 font-normal text-foreground-muted">(required for FPX receipt)</span>
                  </label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground-muted" />
                    <input
                      type="tel"
                      value={fpxPhone}
                      onChange={(e) => setFpxPhone(e.target.value)}
                      placeholder="601XXXXXXXX"
                      className="w-full h-10 rounded-md border border-border bg-background-elevated pl-9 pr-3 text-sm text-foreground-primary placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-primary/20"
                    />
                  </div>
                  <p className="mt-1.5 text-[10px] text-foreground-muted">
                    Format: 601XXXXXXXX · Your bank will send SMS OTP to this number
                  </p>
                </div>
              )}
            </div>

            <p className="mt-3 text-center text-2xs text-foreground-muted">
              {paymentMethod === "fpx"
                ? "Secure FPX payment via Billplz · Malaysian banks supported · No card needed"
                : paymentMethod === "upi"
                  ? "Secure payment via Razorpay · UPI, cards & NetBanking · Trusted by 10M+ Indian businesses"
                  : "Secure checkout via Stripe · Cancel anytime · No hidden fees"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
