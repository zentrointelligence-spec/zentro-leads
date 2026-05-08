"use client";

import { useState } from "react";
import {
  Sparkles,
  Save,
  Loader2,
  Brain,
  MapPin,
  Building2,
  Users,
  Tags,
  Search,
  Zap,
  ChevronRight,
  CheckCircle2,
  Plus,
  Trash2,
  Clock,
  Smartphone,
  Globe,
  Heart,
  DollarSign,
  Calendar,
  Database,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/cn";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

// ── Types ──────────────────────────────────────────────────────────────────────

interface ICPResult {
  id?: string;
  name: string;
  description: string;
  industries: string[];
  job_titles: string[];
  seniority_levels: string[];
  company_sizes: string[];
  locations: string[];
  keywords: string[];
  intent_signals: string[];
  search_queries: string[];
  total_leads_generated?: number;
  conversion_rate?: number;
  is_active?: boolean;
  created_at?: string;
}

interface B2CResult {
  life_stages: string[];
  age_ranges: string[];
  income_brackets: string[];
  life_events: string[];
  insurance_needs: string[];
  locations: string[];
  data_sources: string[];
  outreach_timing: string;
  outreach_channel: string;
  language_preference: string;
  search_queries: string[];
}

type Mode = "b2b" | "b2c";

// ── Shared components ──────────────────────────────────────────────────────────

function TagChip({ label, onRemove }: { label: string; onRemove?: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium text-primary">
      {label}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="ml-0.5 rounded-full hover:bg-primary/20 p-0.5 transition-colors"
          aria-label={`Remove ${label}`}
        >
          <Trash2 className="h-2.5 w-2.5" />
        </button>
      )}
    </span>
  );
}

function ICPSection({
  icon,
  title,
  items,
  color = "primary",
}: {
  icon: React.ReactNode;
  title: string;
  items: string[];
  color?: string;
}) {
  if (!items?.length) return null;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div
          className={cn(
            "flex h-7 w-7 items-center justify-center rounded-lg",
            color === "hot"   ? "bg-red-500/10"     :
            color === "warm"  ? "bg-amber-500/10"   :
            color === "green" ? "bg-emerald-500/10" :
            color === "blue"  ? "bg-blue-500/10"    : "bg-primary/10"
          )}
        >
          {icon}
        </div>
        <span className="text-xs font-semibold text-foreground-secondary uppercase tracking-wide">
          {title}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <TagChip key={item} label={item} />
        ))}
      </div>
    </div>
  );
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-3 rounded-xl border border-border bg-background-elevated px-4 py-3">
      <div className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-primary/10">
        {icon}
      </div>
      <div>
        <p className="text-xs font-semibold text-foreground-secondary uppercase tracking-wide">{label}</p>
        <p className="mt-0.5 text-sm text-foreground-primary">{value}</p>
      </div>
    </div>
  );
}

// ── Mode Toggle ────────────────────────────────────────────────────────────────

function ModeToggle({ mode, onChange }: { mode: Mode; onChange: (m: Mode) => void }) {
  return (
    <div className="inline-flex rounded-xl border border-border bg-background-secondary p-1 gap-1">
      {(["b2b", "b2c"] as Mode[]).map((m) => (
        <button
          key={m}
          type="button"
          onClick={() => onChange(m)}
          className={cn(
            "rounded-lg px-4 py-1.5 text-xs font-semibold transition-all",
            mode === m
              ? "bg-primary text-white shadow-sm"
              : "text-foreground-secondary hover:text-foreground-primary"
          )}
        >
          {m === "b2b" ? "B2B Mode" : "B2C Mode"}
        </button>
      ))}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function ICPBuilderPage() {
  const [mode, setMode] = useState<Mode>("b2b");

  // B2B state
  const [b2bDesc, setB2bDesc] = useState("");
  const [b2bBuilding, setB2bBuilding] = useState(false);
  const [b2bSaving, setB2bSaving] = useState(false);
  const [b2bResult, setB2bResult] = useState<ICPResult | null>(null);
  const [b2bSaved, setB2bSaved] = useState(false);

  // B2C state
  const [b2cDesc, setB2cDesc] = useState("");
  const [b2cMarket, setB2cMarket] = useState<"malaysia" | "india">("malaysia");
  const [b2cFocus, setB2cFocus] = useState("");
  const [b2cBuilding, setB2cBuilding] = useState(false);
  const [b2cResult, setB2cResult] = useState<B2CResult | null>(null);

  // ── B2B handlers ─────────────────────────────────────────────────────────────

  async function handleB2BBuild() {
    const trimmed = b2bDesc.trim();
    if (trimmed.length < 10) {
      toast.error("Describe your ideal customer in at least 10 characters.");
      return;
    }
    setB2bBuilding(true);
    setB2bResult(null);
    setB2bSaved(false);
    try {
      const res = await fetch("/api/v1/icp/build", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ description: trimmed }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "ICP build failed");
      setB2bResult(data as ICPResult);
      toast.success("ICP generated — review and save below.");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to generate ICP");
    } finally {
      setB2bBuilding(false);
    }
  }

  async function handleB2BSave() {
    if (!b2bResult) return;
    setB2bSaving(true);
    try {
      const res = await fetch("/api/v1/icp/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          name: b2bResult.name,
          description: b2bResult.description,
          industries: b2bResult.industries,
          job_titles: b2bResult.job_titles,
          seniority_levels: b2bResult.seniority_levels,
          company_sizes: b2bResult.company_sizes,
          locations: b2bResult.locations,
          keywords: b2bResult.keywords,
          intent_signals: b2bResult.intent_signals,
          search_queries: b2bResult.search_queries,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Save failed");
      setB2bResult((prev) => prev ? { ...prev, id: data.id } : prev);
      setB2bSaved(true);
      toast.success(`ICP "${b2bResult.name}" saved!`, {
        action: {
          label: "Generate Leads",
          onClick: () => (window.location.href = "/dashboard/leads"),
        },
      });
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to save ICP");
    } finally {
      setB2bSaving(false);
    }
  }

  // ── B2C handler ───────────────────────────────────────────────────────────────

  async function handleB2CBuild() {
    const trimmed = b2cDesc.trim();
    if (trimmed.length < 10) {
      toast.error("Describe your ideal prospect in at least 10 characters.");
      return;
    }
    setB2cBuilding(true);
    setB2cResult(null);
    try {
      const res = await fetch("/api/v1/icp/build-b2c", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          description: trimmed,
          market: b2cMarket,
          insurance_focus: b2cFocus || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "B2C ICP build failed");
      setB2cResult(data as B2CResult);
      toast.success("B2C prospect profile generated.");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to generate B2C ICP");
    } finally {
      setB2cBuilding(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="mx-auto max-w-3xl space-y-6 animate-fade-in-up">
      {/* Header + toggle */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-foreground-primary">ICP Builder</h1>
          <p className="mt-0.5 text-sm text-foreground-secondary">
            {mode === "b2b"
              ? "Describe your ideal business customer — Claude builds a complete B2B profile."
              : "Describe your ideal individual prospect — Claude builds a life-event B2C profile."}
          </p>
        </div>
        <ModeToggle mode={mode} onChange={(m) => { setMode(m); }} />
      </div>

      {/* ── B2B MODE ──────────────────────────────────────────────────────────── */}
      {mode === "b2b" && (
        <>
          <Card>
            <CardContent className="p-6 space-y-4">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-primary/10">
                  <Brain className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-foreground-primary">Who is your ideal business customer?</h2>
                  <p className="text-sm text-foreground-muted">Industry, size, location, role — one sentence is enough.</p>
                </div>
              </div>

              <div className="space-y-2">
                <textarea
                  value={b2bDesc}
                  onChange={(e) => setB2bDesc(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleB2BBuild(); }}
                  placeholder="e.g. SME business owners in Malaysia with 5–50 employees who need life or fire insurance but haven't been approached yet"
                  rows={3}
                  className="w-full resize-none rounded-xl border border-border bg-background-elevated px-4 py-3 text-sm text-foreground-primary placeholder:text-foreground-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 transition-all"
                />
                <div className="flex items-center justify-between">
                  <span className="text-xs text-foreground-muted">
                    {b2bDesc.length > 0 && `${b2bDesc.length} chars · `}Press ⌘+Enter to generate
                  </span>
                  <Button
                    onClick={handleB2BBuild}
                    isLoading={b2bBuilding}
                    leftIcon={<Sparkles className="h-4 w-4" />}
                    disabled={b2bDesc.trim().length < 10}
                  >
                    {b2bBuilding ? "Claude is thinking…" : "Build ICP with AI"}
                  </Button>
                </div>
              </div>

              {!b2bResult && !b2bBuilding && (
                <div className="space-y-2 pt-1">
                  <p className="text-xs font-medium text-foreground-muted">Try an example:</p>
                  <div className="flex flex-wrap gap-2">
                    {[
                      "Insurance agents in Malaysia targeting SME motor fleets",
                      "B2B SaaS founders in India Series A looking for group health cover",
                      "Family takaful agents seeking new parents in KL and Selangor",
                    ].map((ex) => (
                      <button
                        key={ex}
                        type="button"
                        onClick={() => setB2bDesc(ex)}
                        className="rounded-full border border-border bg-background-secondary px-3 py-1.5 text-xs text-foreground-secondary hover:border-primary/30 hover:text-foreground-primary transition-colors flex items-center gap-1"
                      >
                        <Plus className="h-3 w-3" />
                        {ex}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {b2bBuilding && <BuildingSkeleton label="Claude is building your B2B ICP profile…" />}

          {b2bResult && !b2bBuilding && (
            <Card className="border-primary/20">
              <CardContent className="p-6 space-y-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-primary/10">
                      <Sparkles className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-foreground-primary">{b2bResult.name}</h3>
                      <p className="text-sm text-foreground-secondary mt-0.5">{b2bResult.description}</p>
                    </div>
                  </div>
                  {b2bSaved ? (
                    <div className="flex items-center gap-1.5 text-sm text-emerald-500 font-medium flex-shrink-0">
                      <CheckCircle2 className="h-4 w-4" /> Saved
                    </div>
                  ) : (
                    <Button
                      onClick={handleB2BSave}
                      isLoading={b2bSaving}
                      leftIcon={<Save className="h-4 w-4" />}
                      className="flex-shrink-0"
                    >
                      Save ICP
                    </Button>
                  )}
                </div>

                <hr className="border-border" />

                <div className="grid gap-5 sm:grid-cols-2">
                  <ICPSection icon={<Building2 className="h-4 w-4 text-primary" />}       title="Target Industries"   items={b2bResult.industries} />
                  <ICPSection icon={<Users className="h-4 w-4 text-amber-500" />}          title="Job Titles"          items={b2bResult.job_titles}      color="warm" />
                  <ICPSection icon={<ChevronRight className="h-4 w-4 text-emerald-500" />} title="Seniority Levels"    items={b2bResult.seniority_levels} color="green" />
                  <ICPSection icon={<Building2 className="h-4 w-4 text-violet-500" />}    title="Company Sizes"       items={b2bResult.company_sizes}   color="warm" />
                  <ICPSection icon={<MapPin className="h-4 w-4 text-primary" />}           title="Locations"           items={b2bResult.locations} />
                  <ICPSection icon={<Tags className="h-4 w-4 text-amber-500" />}           title="Keywords"            items={b2bResult.keywords}        color="warm" />
                  <ICPSection icon={<Zap className="h-4 w-4 text-red-500" />}              title="Intent Signals"      items={b2bResult.intent_signals}  color="hot" />
                  <ICPSection icon={<Search className="h-4 w-4 text-primary" />}           title="Search Queries"      items={b2bResult.search_queries} />
                </div>

                {b2bSaved && (
                  <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-foreground-primary">ICP saved successfully</p>
                      <p className="text-xs text-foreground-muted mt-0.5">Go to Leads and click Generate to find matching leads.</p>
                    </div>
                    <a
                      href="/dashboard/leads"
                      className="flex-shrink-0 flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white hover:bg-primary/90 transition-colors"
                    >
                      Generate Leads <ChevronRight className="h-3.5 w-3.5" />
                    </a>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* ── B2C MODE ──────────────────────────────────────────────────────────── */}
      {mode === "b2c" && (
        <>
          <Card>
            <CardContent className="p-6 space-y-4">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-amber-500/10">
                  <Heart className="h-5 w-5 text-amber-500" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-foreground-primary">Who is your ideal individual prospect?</h2>
                  <p className="text-sm text-foreground-muted">Describe the life stage or event — Claude finds the signals.</p>
                </div>
              </div>

              {/* Market + Insurance focus row */}
              <div className="flex gap-3 flex-wrap">
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-foreground-secondary">Market</label>
                  <select
                    value={b2cMarket}
                    onChange={(e) => setB2cMarket(e.target.value as "malaysia" | "india")}
                    className="rounded-lg border border-border bg-background-elevated px-3 py-2 text-sm text-foreground-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
                  >
                    <option value="malaysia">Malaysia</option>
                    <option value="india">India</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1 flex-1 min-w-[160px]">
                  <label className="text-xs font-medium text-foreground-secondary">Insurance Focus (optional)</label>
                  <select
                    value={b2cFocus}
                    onChange={(e) => setB2cFocus(e.target.value)}
                    className="rounded-lg border border-border bg-background-elevated px-3 py-2 text-sm text-foreground-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
                  >
                    <option value="">Any insurance type</option>
                    <option value="motor">Motor</option>
                    <option value="medical">Medical</option>
                    <option value="life">Life</option>
                    <option value="home">Home</option>
                    <option value="pa">Personal Accident</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <textarea
                  value={b2cDesc}
                  onChange={(e) => setB2cDesc(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleB2CBuild(); }}
                  placeholder="e.g. I want to find people who just bought a new car in Kuala Lumpur aged 25-40"
                  rows={3}
                  className="w-full resize-none rounded-xl border border-border bg-background-elevated px-4 py-3 text-sm text-foreground-primary placeholder:text-foreground-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 transition-all"
                />
                <div className="flex items-center justify-between">
                  <span className="text-xs text-foreground-muted">
                    {b2cDesc.length > 0 && `${b2cDesc.length} chars · `}Press ⌘+Enter to generate
                  </span>
                  <Button
                    onClick={handleB2CBuild}
                    isLoading={b2cBuilding}
                    leftIcon={<Sparkles className="h-4 w-4" />}
                    disabled={b2cDesc.trim().length < 10}
                    className="bg-amber-500 hover:bg-amber-500/90"
                  >
                    {b2cBuilding ? "Claude is thinking…" : "Build B2C Profile"}
                  </Button>
                </div>
              </div>

              {!b2cResult && !b2cBuilding && (
                <div className="space-y-2 pt-1">
                  <p className="text-xs font-medium text-foreground-muted">Try an example:</p>
                  <div className="flex flex-wrap gap-2">
                    {[
                      "New car buyers in Klang Valley needing motor insurance",
                      "Young families in KL who recently had a baby",
                      "First-time homebuyers in Johor Bahru",
                      "Motorcyclists in Penang aged 20-35",
                    ].map((ex) => (
                      <button
                        key={ex}
                        type="button"
                        onClick={() => setB2cDesc(ex)}
                        className="rounded-full border border-border bg-background-secondary px-3 py-1.5 text-xs text-foreground-secondary hover:border-amber-400/40 hover:text-foreground-primary transition-colors flex items-center gap-1"
                      >
                        <Plus className="h-3 w-3" />
                        {ex}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {b2cBuilding && <BuildingSkeleton label="Claude is building your B2C prospect profile…" />}

          {b2cResult && !b2cBuilding && (
            <Card className="border-amber-500/20">
              <CardContent className="p-6 space-y-5">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-amber-500/10">
                    <Heart className="h-5 w-5 text-amber-500" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-foreground-primary">B2C Prospect Profile</h3>
                    <p className="text-sm text-foreground-secondary mt-0.5">{b2cDesc}</p>
                  </div>
                </div>

                <hr className="border-border" />

                <div className="grid gap-5 sm:grid-cols-2">
                  <ICPSection icon={<Users className="h-4 w-4 text-amber-500" />}       title="Life Stages"       items={b2cResult.life_stages}     color="warm" />
                  <ICPSection icon={<Calendar className="h-4 w-4 text-primary" />}      title="Age Ranges"        items={b2cResult.age_ranges} />
                  <ICPSection icon={<DollarSign className="h-4 w-4 text-emerald-500" />} title="Income Brackets"   items={b2cResult.income_brackets} color="green" />
                  <ICPSection icon={<Zap className="h-4 w-4 text-red-500" />}           title="Life Events"       items={b2cResult.life_events}     color="hot" />
                  <ICPSection icon={<Heart className="h-4 w-4 text-amber-500" />}       title="Insurance Needs"   items={b2cResult.insurance_needs} color="warm" />
                  <ICPSection icon={<MapPin className="h-4 w-4 text-primary" />}        title="Locations"         items={b2cResult.locations} />
                  <ICPSection icon={<Database className="h-4 w-4 text-blue-500" />}    title="Data Sources"      items={b2cResult.data_sources}    color="blue" />
                  <ICPSection icon={<Search className="h-4 w-4 text-primary" />}        title="Search Angles"     items={b2cResult.search_queries} />
                </div>

                <hr className="border-border" />

                <div className="grid gap-3 sm:grid-cols-3">
                  <InfoRow
                    icon={<Clock className="h-4 w-4 text-primary" />}
                    label="Outreach Timing"
                    value={b2cResult.outreach_timing}
                  />
                  <InfoRow
                    icon={<Smartphone className="h-4 w-4 text-emerald-500" />}
                    label="Outreach Channel"
                    value={b2cResult.outreach_channel}
                  />
                  <InfoRow
                    icon={<Globe className="h-4 w-4 text-amber-500" />}
                    label="Language"
                    value={b2cResult.language_preference}
                  />
                </div>

                <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-foreground-primary">Profile ready</p>
                    <p className="text-xs text-foreground-muted mt-0.5">
                      Use these signals to build B2C lead scraping campaigns.
                    </p>
                  </div>
                  <a
                    href="/dashboard/leads"
                    className="flex-shrink-0 flex items-center gap-1.5 rounded-lg bg-amber-500 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-500/90 transition-colors"
                  >
                    Generate Leads <ChevronRight className="h-3.5 w-3.5" />
                  </a>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

// ── Shared loading skeleton ────────────────────────────────────────────────────

function BuildingSkeleton({ label }: { label: string }) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center gap-3 mb-5">
          <Loader2 className="h-5 w-5 text-primary animate-spin" />
          <span className="text-sm font-medium text-foreground-primary">{label}</span>
        </div>
        <div className="space-y-3">
          {[80, 60, 70, 50, 65].map((w, i) => (
            <div key={i} className="h-3 rounded-full bg-border animate-pulse" style={{ width: `${w}%` }} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
