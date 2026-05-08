"use client";

import { useState, useTransition } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  MoreHorizontal,
  Shield,
  UserX,
  KeyRound,
  ExternalLink,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import type { AdminUserListItem, AdminUserListResponse } from "@/lib/api";

interface Props {
  initialData:   AdminUserListResponse;
  page:          number;
  limit:         number;
  initialSearch: string;
  initialRole:   string;
  initialPlan:   string;
  initialStatus: string;
}

const PLAN_COLORS: Record<string, string> = {
  free:    "bg-gray-800 text-gray-400",
  starter: "bg-blue-900/60 text-blue-300",
  growth:  "bg-indigo-900/60 text-indigo-300",
  pro:     "bg-purple-900/60 text-purple-300",
  agency:  "bg-orange-900/60 text-orange-300",
};

const ROLE_COLORS: Record<string, string> = {
  agent: "bg-gray-800 text-gray-400",
  owner: "bg-emerald-900/60 text-emerald-300",
  admin: "bg-red-900/60 text-red-300",
};

function Badge({ label, colorClass }: { label: string; colorClass: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${colorClass}`}>
      {label}
    </span>
  );
}

function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  danger,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="rounded-xl bg-gray-900 border border-gray-700 p-6 max-w-sm w-full mx-4">
        <h3 className="text-base font-bold text-white mb-2">{title}</h3>
        <p className="text-sm text-gray-400 mb-6">{description}</p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={`rounded-lg px-4 py-2 text-sm font-semibold text-white transition-colors ${
              danger ? "bg-red-600 hover:bg-red-700" : "bg-orange-600 hover:bg-orange-700"
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

function ResetPasswordModal({
  open,
  userId,
  userName,
  onClose,
}: {
  open: boolean;
  userId: string;
  userName: string;
  onClose: () => void;
}) {
  const [pw, setPw]           = useState("");
  const [busy, setBusy]       = useState(false);

  if (!open) return null;

  const handleSubmit = async () => {
    if (pw.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }
    setBusy(true);
    try {
      const res = await fetch(`/api/admin/users/${userId}/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_password: pw }),
      });
      if (!res.ok) throw new Error("Failed");
      toast.success(`Password reset for ${userName}`);
      setPw("");
      onClose();
    } catch {
      toast.error("Failed to reset password");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="rounded-xl bg-gray-900 border border-gray-700 p-6 max-w-sm w-full mx-4">
        <h3 className="text-base font-bold text-white mb-1">Reset Password</h3>
        <p className="text-sm text-gray-500 mb-5">{userName}</p>
        <input
          type="password"
          placeholder="New password (min 8 chars)"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          className="w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-orange-500 mb-4"
        />
        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-400 hover:text-white"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={busy}
            className="rounded-lg bg-orange-600 hover:bg-orange-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy ? "Resetting…" : "Reset"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ActionMenu({ user, onRefresh }: { user: AdminUserListItem; onRefresh: () => void }) {
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState<{
    type: "admin" | "deactivate" | "delete";
  } | null>(null);
  const [resetOpen, setResetOpen] = useState(false);

  const patch = async (payload: Record<string, unknown>) => {
    const res = await fetch(`/api/admin/users/${user.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed");
  };

  const handleMakeAdmin = async () => {
    try {
      await patch({ role: "admin" });
      toast.success(`${user.full_name} is now an admin`);
      onRefresh();
    } catch {
      toast.error("Failed to update role");
    }
  };

  const handleDeactivate = async () => {
    try {
      await patch({ is_active: false });
      toast.success(`${user.full_name} deactivated`);
      onRefresh();
    } catch {
      toast.error("Failed to deactivate");
    }
  };

  const handlePlanChange = async (plan: string) => {
    try {
      await patch({ plan });
      toast.success(`Plan changed to ${plan}`);
      onRefresh();
    } catch {
      toast.error("Failed to change plan");
    }
  };

  return (
    <>
      <ConfirmDialog
        open={confirm?.type === "admin"}
        title="Promote to Admin?"
        description={`This will give ${user.full_name} full admin access to the platform. This action can be reversed.`}
        confirmLabel="Make Admin"
        onConfirm={() => { setConfirm(null); handleMakeAdmin(); }}
        onCancel={() => setConfirm(null)}
      />
      <ConfirmDialog
        open={confirm?.type === "deactivate"}
        title="Deactivate Account?"
        description={`${user.full_name}'s account will be deactivated immediately. Their leads and data are preserved.`}
        confirmLabel="Deactivate"
        danger
        onConfirm={() => { setConfirm(null); handleDeactivate(); }}
        onCancel={() => setConfirm(null)}
      />
      <ResetPasswordModal
        open={resetOpen}
        userId={user.id}
        userName={user.full_name}
        onClose={() => setResetOpen(false)}
      />

      <div className="relative">
        <button
          onClick={() => setOpen((o) => !o)}
          className="rounded-md p-1.5 text-gray-500 hover:bg-gray-800 hover:text-white transition-colors"
        >
          <MoreHorizontal className="h-4 w-4" />
        </button>

        {open && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
            <div className="absolute right-0 top-8 z-20 w-52 rounded-xl bg-gray-800 border border-gray-700 shadow-xl py-1">
              <Link
                href={`/dashboard/admin/users/${user.id}`}
                className="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-300 hover:bg-gray-700 hover:text-white"
                onClick={() => setOpen(false)}
              >
                <ExternalLink className="h-3.5 w-3.5" />
                View Details
              </Link>

              <div className="border-t border-gray-700 my-1" />

              <p className="px-4 py-1 text-[10px] uppercase tracking-wider text-gray-600">Change Plan</p>
              {(["free","starter","growth","pro","agency"] as const).map((p) => (
                <button
                  key={p}
                  onClick={() => { setOpen(false); handlePlanChange(p); }}
                  className="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white capitalize"
                >
                  {user.plan === p && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />}
                  {user.plan !== p && <span className="w-3.5" />}
                  {p}
                </button>
              ))}

              <div className="border-t border-gray-700 my-1" />

              {user.role !== "admin" && (
                <button
                  onClick={() => { setOpen(false); setConfirm({ type: "admin" }); }}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-orange-400 hover:bg-gray-700"
                >
                  <Shield className="h-3.5 w-3.5" />
                  Make Admin
                </button>
              )}

              <button
                onClick={() => { setOpen(false); setResetOpen(true); }}
                className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-gray-300 hover:bg-gray-700 hover:text-white"
              >
                <KeyRound className="h-3.5 w-3.5" />
                Reset Password
              </button>

              {user.is_active && (
                <button
                  onClick={() => { setOpen(false); setConfirm({ type: "deactivate" }); }}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-red-400 hover:bg-gray-700"
                >
                  <UserX className="h-3.5 w-3.5" />
                  Deactivate
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </>
  );
}

export function AdminUsersClient({
  initialData,
  page,
  limit,
  initialSearch,
  initialRole,
  initialPlan,
  initialStatus,
}: Props) {
  const router       = useRouter();
  const pathname     = usePathname();
  const [, startT]   = useTransition();

  const [search, setSearch]   = useState(initialSearch);
  const [role, setRole]       = useState(initialRole);
  const [plan, setPlan]       = useState(initialPlan);
  const [status, setStatus]   = useState(initialStatus);

  const [data]                = useState<AdminUserListResponse>(initialData);

  const totalPages = Math.max(1, Math.ceil(data.total / limit));

  const applyFilters = (overrides: Record<string, string> = {}) => {
    const params = new URLSearchParams();
    const s = overrides.search  ?? search;
    const r = overrides.role    ?? role;
    const p = overrides.plan    ?? plan;
    const a = overrides.status  ?? status;
    if (s) params.set("search", s);
    if (r) params.set("role", r);
    if (p) params.set("plan", p);
    if (a) params.set("is_active", a);
    params.set("page", "1");
    startT(() => router.push(`${pathname}?${params.toString()}`));
  };

  const goPage = (n: number) => {
    const params = new URLSearchParams(window.location.search);
    params.set("page", String(n));
    startT(() => router.push(`${pathname}?${params.toString()}`));
  };

  const refresh = () => {
    startT(() => router.refresh());
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Users</h1>
          <p className="text-sm text-gray-500 mt-0.5">{data.total.toLocaleString()} total accounts</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-600" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && applyFilters({ search })}
            placeholder="Search email or agency…"
            className="w-full rounded-lg bg-gray-900 border border-gray-700 pl-9 pr-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-orange-500"
          />
        </div>

        <select
          value={role}
          onChange={(e) => { setRole(e.target.value); applyFilters({ role: e.target.value }); }}
          className="rounded-lg bg-gray-900 border border-gray-700 px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-orange-500"
        >
          <option value="">All Roles</option>
          <option value="agent">Agent</option>
          <option value="owner">Owner</option>
          <option value="admin">Admin</option>
        </select>

        <select
          value={plan}
          onChange={(e) => { setPlan(e.target.value); applyFilters({ plan: e.target.value }); }}
          className="rounded-lg bg-gray-900 border border-gray-700 px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-orange-500"
        >
          <option value="">All Plans</option>
          <option value="free">Free</option>
          <option value="starter">Starter</option>
          <option value="growth">Growth</option>
          <option value="pro">Pro</option>
          <option value="agency">Agency</option>
        </select>

        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); applyFilters({ status: e.target.value }); }}
          className="rounded-lg bg-gray-900 border border-gray-700 px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-orange-500"
        >
          <option value="">All Status</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>

        <button
          onClick={() => applyFilters({ search })}
          className="rounded-lg bg-orange-600 hover:bg-orange-700 px-4 py-2 text-sm font-semibold text-white transition-colors"
        >
          Apply
        </button>
      </div>

      {/* Table */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                {["Agency / Email", "Plan", "Role", "Leads", "ICPs", "Joined", "Status", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-600">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-gray-600">
                    No users found
                  </td>
                </tr>
              )}
              {data.items.map((user) => (
                <tr
                  key={user.id}
                  className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors"
                >
                  <td className="px-4 py-3">
                    <p className="font-semibold text-white truncate max-w-[180px]">
                      {user.company_name || user.full_name}
                    </p>
                    <p className="text-xs text-gray-500 truncate max-w-[180px]">{user.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <Badge label={user.plan} colorClass={PLAN_COLORS[user.plan] ?? "bg-gray-800 text-gray-400"} />
                  </td>
                  <td className="px-4 py-3">
                    <Badge label={user.role} colorClass={ROLE_COLORS[user.role] ?? "bg-gray-800 text-gray-400"} />
                  </td>
                  <td className="px-4 py-3 tabular-nums text-gray-300">{user.lead_count.toLocaleString()}</td>
                  <td className="px-4 py-3 tabular-nums text-gray-300">{user.icp_count}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                    {new Date(user.created_at).toLocaleDateString("en-MY", { day: "numeric", month: "short", year: "numeric" })}
                  </td>
                  <td className="px-4 py-3">
                    {user.is_active ? (
                      <span className="flex items-center gap-1.5 text-emerald-400 text-xs font-medium">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Active
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5 text-red-400 text-xs font-medium">
                        <XCircle className="h-3.5 w-3.5" /> Inactive
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <ActionMenu user={user} onRefresh={refresh} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-800">
          <p className="text-xs text-gray-600">
            Page {page} of {totalPages} · {data.total} users
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => goPage(page - 1)}
              disabled={page <= 1}
              className="rounded-lg border border-gray-700 p-2 text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => goPage(page + 1)}
              disabled={page >= totalPages}
              className="rounded-lg border border-gray-700 p-2 text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
