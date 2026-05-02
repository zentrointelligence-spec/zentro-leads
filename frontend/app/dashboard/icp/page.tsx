"use client";

import { useState, useTransition } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Target,
  Plus,
  Loader2,
  X,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Zap,
  Building2,
  MapPin,
  Briefcase,
  BarChart3,
  Search,
  Tag,
  Activity,
  Pencil,
  Trash2,
  Save,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { generateLeads } from "@/app/dashboard/leads/actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

interface ICP {
  id: string;
  name: string;
  description: string | null;
  industries: string[];
  job_titles: string[];
  seniority_levels: string[];
  company_sizes: string[];
  locations: string[];
  keywords: string[];
  intent_signals: string[];
  search_queries: string[];
  total_leads_generated: number;
  conversion_rate: number;
  is_active: boolean;
  created_at: string;
}

interface ICPListResponse {
  items: ICP[];
  total: number;
}

async function fetchICPs(): Promise<ICPListResponse> {
  const res = await fetch("/api/v1/icp/", { credentials: "include" });
  if (!res.ok) throw new Error("Failed to load ICPs");
  return res.json();
}

async function buildICPWithAI(description: string): Promise<ICP> {
  const res = await fetch("/api/v1/icp/build", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ description }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? "Failed to build ICP");
  return json;
}

async function createICP(body: {
  name: string;
  description?: string;
  industries?: string[];
  job_titles?: string[];
  company_sizes?: string[];
  locations?: string[];
  keywords?: string[];
}): Promise<ICP> {
  const res = await fetch("/api/v1/icp/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? "Failed to create ICP");
  return json;
}

async function updateICP(
  id: string,
  body: { name?: string; description?: string; industries?: string[]; job_titles?: string[] }
): Promise<ICP> {
  const res = await fetch(`/api/v1/icp/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? "Failed to update ICP");
  return json;
}

async function deleteICP(id: string): Promise<{ message: string }> {
  const res = await fetch(`/api/v1/icp/${id}`, {
    method: "DELETE",
    credentials: "include",
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? "Failed to delete ICP");
  return json;
}

const TAG_META: Record<string, { icon: React.ElementType; color: string }> = {
  Industries: { icon: Building2, color: "bg-primary-light text-primary border-primary/20" },
  "Job Titles": { icon: Briefcase, color: "bg-accent-light text-accent-dark border-accent/20 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800" },
  Seniority: { icon: BarChart3, color: "bg-warm-light text-warm border-warm/20" },
  "Company Sizes": { icon: Building2, color: "bg-success-light text-success border-success/20" },
  Locations: { icon: MapPin, color: "bg-cyan-100 text-cyan-600 border-cyan-200 dark:bg-cyan-900/30 dark:text-cyan-400 dark:border-cyan-800" },
  Keywords: { icon: Tag, color: "bg-orange-100 text-orange-600 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800" },
  "Intent Signals": { icon: Activity, color: "bg-hot-light text-hot border-hot/20" },
};

/* ── Tag Input ───────────────────────────────── */

function TagInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string[];
  onChange: (vals: string[]) => void;
  placeholder?: string;
}) {
  const [text, setText] = useState("");

  function addTag() {
    const trimmed = text.trim();
    if (!trimmed) return;
    const tags = trimmed.split(",").map((t) => t.trim()).filter(Boolean);
    const next = [...new Set([...value, ...tags])];
    onChange(next);
    setText("");
  }

  function removeTag(tag: string) {
    onChange(value.filter((v) => v !== tag));
  }

  return (
    <div>
      <label className="block text-sm font-medium text-foreground-primary mb-1.5">
        {label}
      </label>
      <div className="flex gap-2">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addTag();
            }
          }}
          placeholder={placeholder ?? "Add tag and press Enter"}
          className="flex-1 rounded-md border border-border bg-background-elevated px-3 py-2 text-sm text-foreground-primary placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
        <Button type="button" size="sm" onClick={addTag}>
          Add
        </Button>
      </div>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {value.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 rounded-full bg-background-secondary px-2.5 py-0.5 text-2xs font-medium text-foreground-secondary"
            >
              {tag}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                className="text-foreground-muted hover:text-hot"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── ICPCard ─────────────────────────────────── */

function ICPCard({
  icp,
  onEdit,
  onDelete,
}: {
  icp: ICP;
  onEdit: (icp: ICP) => void;
  onDelete: (icp: ICP) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [isPending, startTransition] = useTransition();

  function handleGenerate(e: React.MouseEvent) {
    e.stopPropagation();
    startTransition(async () => {
      const result = await generateLeads(icp.id);
      if (result.ok) {
        toast.success(result.message ?? "Lead generation started — results appear shortly.");
      } else {
        toast.error(result.error ?? "Lead generation failed.");
      }
    });
  }

  const tagGroups = [
    { label: "Industries", values: icp.industries },
    { label: "Job Titles", values: icp.job_titles },
    { label: "Seniority", values: icp.seniority_levels },
    { label: "Company Sizes", values: icp.company_sizes },
    { label: "Locations", values: icp.locations },
    { label: "Keywords", values: icp.keywords },
    { label: "Intent Signals", values: icp.intent_signals },
  ];

  return (
    <Card className="overflow-hidden transition-all hover:shadow-md">
      <div
        className="p-5 cursor-pointer hover:bg-background-secondary/30 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-7 h-7 rounded-md bg-primary-light flex items-center justify-center flex-shrink-0">
                <Target className="w-4 h-4 text-primary" />
              </div>
              <h3 className="text-foreground-primary font-semibold text-sm truncate">
                {icp.name}
              </h3>
            </div>
            {icp.description && (
              <p className="text-foreground-secondary text-xs leading-relaxed line-clamp-2 ml-9">
                {icp.description}
              </p>
            )}
            <div className="flex items-center gap-3 mt-3 ml-9">
              <Badge variant="secondary" className="text-2xs">
                {icp.total_leads_generated} leads
              </Badge>
              <Badge variant="outline" className="text-2xs">
                {icp.industries.length} industries
              </Badge>
              {icp.conversion_rate > 0 && (
                <Badge variant="success" className="text-2xs">
                  {icp.conversion_rate}% conv.
                </Badge>
              )}
            </div>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit(icp);
              }}
              className="rounded-md p-1.5 text-foreground-muted hover:bg-background-secondary hover:text-foreground-primary transition-colors"
              title="Edit ICP"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(icp);
              }}
              className="rounded-md p-1.5 text-foreground-muted hover:bg-hot-light hover:text-hot transition-colors"
              title="Delete ICP"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleGenerate}
              disabled={isPending}
              className="h-8 text-2xs ml-1"
            >
              {isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
              ) : (
                <Zap className="w-3.5 h-3.5 mr-1" />
              )}
              {isPending ? "Starting…" : "Generate"}
            </Button>
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-foreground-muted" />
            ) : (
              <ChevronDown className="w-4 h-4 text-foreground-muted" />
            )}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-border p-5 space-y-4 bg-background-secondary/20">
          {tagGroups.map(({ label, values }) => {
            if (values.length === 0) return null;
            const meta =
              TAG_META[label] ?? {
                icon: Tag,
                color:
                  "bg-background-secondary text-foreground-secondary border-border",
              };
            const Icon = meta.icon;
            return (
              <div key={label}>
                <div className="flex items-center gap-1.5 mb-2">
                  <Icon className="h-3.5 w-3.5 text-foreground-muted" />
                  <p className="text-foreground-muted text-2xs font-semibold uppercase tracking-wide">
                    {label}
                  </p>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {values.map((v) => (
                    <span
                      key={v}
                      className={cn(
                        "text-2xs px-2.5 py-1 rounded-full font-medium border",
                        meta.color
                      )}
                    >
                      {v}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
          {icp.search_queries.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Search className="h-3.5 w-3.5 text-foreground-muted" />
                <p className="text-foreground-muted text-2xs font-semibold uppercase tracking-wide">
                  Search Queries
                </p>
              </div>
              <div className="space-y-1.5">
                {icp.search_queries.map((q) => (
                  <div
                    key={q}
                    className="flex items-start gap-2 text-xs text-foreground-secondary"
                  >
                    <span className="text-primary mt-0.5 flex-shrink-0">›</span>
                    {q}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

/* ── Main Page ───────────────────────────────── */

type ModalMode = "ai" | "manual" | "edit" | null;

export default function ICPPage() {
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [editingIcp, setEditingIcp] = useState<ICP | null>(null);
  const [deletingIcp, setDeletingIcp] = useState<ICP | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["icps"],
    queryFn: fetchICPs,
    refetchInterval: 15000,
    refetchOnWindowFocus: true,
  });

  /* AI Build */
  const [aiDescription, setAiDescription] = useState("");
  const buildMutation = useMutation({
    mutationFn: buildICPWithAI,
    onSuccess: () => {
      toast.success("ICP built successfully!");
      queryClient.invalidateQueries({ queryKey: ["icps"] });
      closeModal();
    },
    onError: (err: Error) => toast.error(err.message),
  });

  /* Manual Create */
  const [manualForm, setManualForm] = useState({
    name: "",
    description: "",
    industries: [] as string[],
    job_titles: [] as string[],
    company_sizes: [] as string[],
    locations: [] as string[],
    keywords: [] as string[],
  });
  const createMutation = useMutation({
    mutationFn: createICP,
    onSuccess: () => {
      toast.success("ICP created!");
      queryClient.invalidateQueries({ queryKey: ["icps"] });
      closeModal();
    },
    onError: (err: Error) => toast.error(err.message),
  });

  /* Edit */
  const [editForm, setEditForm] = useState({
    name: "",
    description: "",
    industries: [] as string[],
    job_titles: [] as string[],
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Parameters<typeof updateICP>[1] }) =>
      updateICP(id, body),
    onSuccess: () => {
      toast.success("ICP updated!");
      queryClient.invalidateQueries({ queryKey: ["icps"] });
      closeModal();
    },
    onError: (err: Error) => toast.error(err.message),
  });

  /* Delete */
  const deleteMutation = useMutation({
    mutationFn: deleteICP,
    onSuccess: () => {
      toast.success("ICP deleted");
      queryClient.invalidateQueries({ queryKey: ["icps"] });
      setDeletingIcp(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function closeModal() {
    setModalMode(null);
    setEditingIcp(null);
    setAiDescription("");
    setManualForm({
      name: "",
      description: "",
      industries: [],
      job_titles: [],
      company_sizes: [],
      locations: [],
      keywords: [],
    });
  }

  function openEdit(icp: ICP) {
    setEditingIcp(icp);
    setEditForm({
      name: icp.name,
      description: icp.description ?? "",
      industries: icp.industries,
      job_titles: icp.job_titles,
    });
    setModalMode("edit");
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground-primary">
            ICP Builder
          </h2>
          <p className="text-foreground-secondary text-sm mt-0.5">
            Define your Ideal Customer Profile — AI builds targeting criteria from
            one sentence.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={() => setModalMode("manual")}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            Create Manually
          </Button>
          <Button onClick={() => setModalMode("ai")} leftIcon={<Sparkles className="w-4 h-4" />}>
            AI Build
          </Button>
        </div>
      </div>

      {/* ICP List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 text-primary animate-spin" />
        </div>
      ) : data?.items.length === 0 ? (
        <Card className="py-16">
          <CardContent className="flex flex-col items-center text-center">
            <div className="w-14 h-14 rounded-2xl bg-primary-light flex items-center justify-center mb-4">
              <Target className="w-7 h-7 text-primary" />
            </div>
            <p className="text-foreground-primary font-semibold mb-2">
              No ICPs yet
            </p>
            <p className="text-foreground-secondary text-sm mb-6 max-w-xs">
              Describe your business in one sentence and let AI build your complete
              targeting criteria.
            </p>
            <div className="flex items-center gap-2">
              <Button variant="secondary" onClick={() => setModalMode("manual")}>
                <Plus className="w-4 h-4 mr-1.5" />
                Create manually
              </Button>
              <Button onClick={() => setModalMode("ai")}>
                <Sparkles className="w-4 h-4 mr-1.5" />
                Build with AI
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {data?.items.map((icp) => (
            <ICPCard
              key={icp.id}
              icp={icp}
              onEdit={openEdit}
              onDelete={(icp) => setDeletingIcp(icp)}
            />
          ))}
        </div>
      )}

      {/* Create / Edit Modal */}
      {modalMode && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-lg shadow-2xl border-border max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-border flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-primary-light flex items-center justify-center">
                  {modalMode === "ai" ? (
                    <Sparkles className="w-5 h-5 text-primary" />
                  ) : modalMode === "edit" ? (
                    <Pencil className="w-5 h-5 text-primary" />
                  ) : (
                    <Plus className="w-5 h-5 text-primary" />
                  )}
                </div>
                <div>
                  <h3 className="text-foreground-primary font-semibold">
                    {modalMode === "ai"
                      ? "AI ICP Builder"
                      : modalMode === "edit"
                        ? "Edit ICP"
                        : "Create ICP Manually"}
                  </h3>
                  <p className="text-foreground-muted text-2xs">
                    {modalMode === "ai"
                      ? "Powered by Claude"
                      : modalMode === "edit"
                        ? "Update your targeting criteria"
                        : "Build your ICP step by step"}
                  </p>
                </div>
              </div>
              <button
                onClick={closeModal}
                className="text-foreground-muted hover:text-foreground-primary transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto flex-1 space-y-4">
              {modalMode === "ai" && (
                <>
                  <label className="block text-foreground-secondary text-sm font-medium mb-2">
                    Describe what you sell (1–3 sentences)
                  </label>
                  <textarea
                    value={aiDescription}
                    onChange={(e) => setAiDescription(e.target.value)}
                    rows={4}
                    placeholder="e.g. I sell health insurance to SME companies in Malaysia with 10–200 employees"
                    className="w-full px-3.5 py-3 rounded-lg bg-background-primary border border-border text-foreground-primary placeholder:text-foreground-muted text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent"
                  />
                  <p className="text-foreground-muted text-xs mt-1.5">
                    Claude will generate industries, job titles, company sizes,
                    locations, keywords, and intent signals.
                  </p>
                </>
              )}

              {(modalMode === "manual" || modalMode === "edit") && (
                <>
                  <Input
                    label="ICP Name"
                    placeholder="e.g. Malaysian SME Health Insurance"
                    value={modalMode === "edit" ? editForm.name : manualForm.name}
                    onChange={(e) =>
                      modalMode === "edit"
                        ? setEditForm((f) => ({ ...f, name: e.target.value }))
                        : setManualForm((f) => ({ ...f, name: e.target.value }))
                    }
                  />
                  <div>
                    <label className="block text-sm font-medium text-foreground-primary mb-1.5">
                      Description
                    </label>
                    <textarea
                      rows={3}
                      placeholder="Brief description of this ICP"
                      className="w-full px-3.5 py-3 rounded-lg bg-background-primary border border-border text-foreground-primary placeholder:text-foreground-muted text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent"
                      value={
                        modalMode === "edit"
                          ? editForm.description
                          : manualForm.description
                      }
                      onChange={(e) =>
                        modalMode === "edit"
                          ? setEditForm((f) => ({
                              ...f,
                              description: e.target.value,
                            }))
                          : setManualForm((f) => ({
                              ...f,
                              description: e.target.value,
                            }))
                      }
                    />
                  </div>
                  <TagInput
                    label="Industries"
                    value={
                      modalMode === "edit"
                        ? editForm.industries
                        : manualForm.industries
                    }
                    onChange={(vals) =>
                      modalMode === "edit"
                        ? setEditForm((f) => ({ ...f, industries: vals }))
                        : setManualForm((f) => ({ ...f, industries: vals }))
                    }
                    placeholder="e.g. Healthcare, Finance, Technology"
                  />
                  <TagInput
                    label="Job Titles"
                    value={
                      modalMode === "edit"
                        ? editForm.job_titles
                        : manualForm.job_titles
                    }
                    onChange={(vals) =>
                      modalMode === "edit"
                        ? setEditForm((f) => ({ ...f, job_titles: vals }))
                        : setManualForm((f) => ({ ...f, job_titles: vals }))
                    }
                    placeholder="e.g. CEO, HR Manager, Founder"
                  />
                  {modalMode === "manual" && (
                    <>
                      <TagInput
                        label="Company Sizes"
                        value={manualForm.company_sizes}
                        onChange={(vals) =>
                          setManualForm((f) => ({ ...f, company_sizes: vals }))
                        }
                        placeholder="e.g. 1-10, 11-50, 51-200"
                      />
                      <TagInput
                        label="Locations"
                        value={manualForm.locations}
                        onChange={(vals) =>
                          setManualForm((f) => ({ ...f, locations: vals }))
                        }
                        placeholder="e.g. Kuala Lumpur, Selangor, Johor"
                      />
                      <TagInput
                        label="Keywords"
                        value={manualForm.keywords}
                        onChange={(vals) =>
                          setManualForm((f) => ({ ...f, keywords: vals }))
                        }
                        placeholder="e.g. insurance, employee benefits"
                      />
                    </>
                  )}
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div className="flex gap-3 px-6 pb-6 flex-shrink-0">
              <Button
                variant="outline"
                className="flex-1"
                onClick={closeModal}
              >
                Cancel
              </Button>
              {modalMode === "ai" && (
                <Button
                  className="flex-1"
                  onClick={() => buildMutation.mutate(aiDescription)}
                  disabled={aiDescription.trim().length < 10 || buildMutation.isPending}
                  isLoading={buildMutation.isPending}
                >
                  <Sparkles className="w-4 h-4 mr-1.5" />
                  Build ICP
                </Button>
              )}
              {modalMode === "manual" && (
                <Button
                  className="flex-1"
                  onClick={() => createMutation.mutate(manualForm)}
                  disabled={!manualForm.name.trim() || createMutation.isPending}
                  isLoading={createMutation.isPending}
                >
                  <Save className="w-4 h-4 mr-1.5" />
                  Save ICP
                </Button>
              )}
              {modalMode === "edit" && editingIcp && (
                <Button
                  className="flex-1"
                  onClick={() =>
                    updateMutation.mutate({
                      id: editingIcp.id,
                      body: {
                        name: editForm.name,
                        description: editForm.description,
                        industries: editForm.industries,
                        job_titles: editForm.job_titles,
                      },
                    })
                  }
                  disabled={!editForm.name.trim() || updateMutation.isPending}
                  isLoading={updateMutation.isPending}
                >
                  <Save className="w-4 h-4 mr-1.5" />
                  Update ICP
                </Button>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* Delete Confirmation */}
      {deletingIcp && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-sm shadow-2xl border-border">
            <div className="p-6 text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-hot-light">
                <Trash2 className="h-6 w-6 text-hot" />
              </div>
              <h3 className="text-lg font-semibold text-foreground-primary">
                Delete ICP
              </h3>
              <p className="mt-2 text-sm text-foreground-secondary">
                Delete <span className="font-medium text-foreground-primary">{deletingIcp.name}</span>? This cannot be undone.
              </p>
              <div className="mt-6 flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setDeletingIcp(null)}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  className="flex-1"
                  onClick={() => deleteMutation.mutate(deletingIcp.id)}
                  isLoading={deleteMutation.isPending}
                >
                  Delete
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
