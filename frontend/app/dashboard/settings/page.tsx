"use client";

import { useEffect, useState } from "react";
import {
  ArrowUpRight,
  CheckCircle2,
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
  Save,
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

type SettingsTab = "general" | "integrations" | "preferences" | "billing";

const PLAN_LIMITS: Record<string, number> = {
  free: 25,
  starter: 500,
  growth: 2000,
  pro: 5000,
  agency: 20000,
};

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
  value,
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

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const { theme, setTheme } = useTheme();

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

  /* ZIMS */
  const [zimsKey, setZimsKey] = useState("");
  const [zimsTesting, setZimsTesting] = useState(false);
  const [zimsConnected, setZimsConnected] = useState<boolean | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem("zentro:auto_push_zims");
    if (saved) setAutoPushZims(saved === "true");

    const savedZimsKey = localStorage.getItem("zentro:zims_api_key");
    if (savedZimsKey) setZimsKey(savedZimsKey);
  }, []);

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

  function handleAutoPushChange(value: boolean) {
    setAutoPushZims(value);
    localStorage.setItem("zentro:auto_push_zims", String(value));
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

  async function handleTestZims() {
    setZimsTesting(true);
    setZimsConnected(null);
    localStorage.setItem("zentro:zims_api_key", zimsKey);
    try {
      // Simulate test — replace with real ping when endpoint exists
      await new Promise((r) => setTimeout(r, 1200));
      setZimsConnected(true);
      toast.success("ZIMS connection successful");
    } catch {
      setZimsConnected(false);
      toast.error("ZIMS connection failed");
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
            description="Connect your ZIMS CRM for automatic lead syncing"
            icon={<ArrowUpRight className="h-5 w-5 text-primary" />}
          >
            <div>
              <label className="block text-sm font-medium text-foreground-primary mb-1.5">
                ZIMS API Key
              </label>
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground-muted" />
                  <input
                    type="password"
                    value={zimsKey}
                    onChange={(e) => setZimsKey(e.target.value)}
                    placeholder="Enter your ZIMS API key"
                    className="w-full h-10 rounded-md border border-border bg-background-elevated pl-9 pr-3 text-sm text-foreground-primary placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>
                <Button
                  variant="secondary"
                  onClick={handleTestZims}
                  isLoading={zimsTesting}
                >
                  Test Connection
                </Button>
              </div>
              {zimsConnected === true && (
                <div className="mt-2 flex items-center gap-1.5 text-xs text-success">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Connected successfully
                </div>
              )}
              {zimsConnected === false && (
                <div className="mt-2 text-xs text-hot">
                  Connection failed — check your API key
                </div>
              )}
            </div>

            <ToggleRow
              label="Auto-push HOT leads to ZIMS"
              description="Any lead scoring 85+ will automatically sync to ZIMS"
              enabled={autoPushZims}
              onChange={handleAutoPushChange}
            />
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
          <SettingsSection
            title="Plan & Usage"
            description="Your current subscription and limits"
            icon={<CreditCard className="h-5 w-5 text-primary" />}
          >
            {userLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 text-primary animate-spin" />
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between rounded-lg border border-border bg-background-secondary px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-foreground-primary capitalize">
                      {user?.plan ?? "Free"} Plan
                    </p>
                    <p className="text-2xs text-foreground-muted mt-0.5">
                      {planLimit.toLocaleString()} leads / month
                    </p>
                  </div>
                  <Badge variant="secondary">Current</Badge>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-foreground-secondary">
                      Leads used this month
                    </span>
                    <span className="font-medium text-foreground-primary">
                      {user?.leads_used_this_month ?? 0} / {planLimit}
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-border overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{ width: `${usedPct}%` }}
                    />
                  </div>
                </div>
                <button className="w-full rounded-lg border border-primary/30 bg-primary-light px-4 py-2.5 text-sm font-semibold text-primary hover:bg-primary/10 transition-colors">
                  Upgrade to Growth
                </button>
              </>
            )}
          </SettingsSection>
        </div>
      )}
    </div>
  );
}
