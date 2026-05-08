import { adminApi } from "@/lib/api";
import { AdminUsersClient } from "./_components/admin-users-client";

export const dynamic = "force-dynamic";

export default async function AdminUsersPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string>>;
}) {
  const sp    = await searchParams;
  const page  = Math.max(1, parseInt(sp.page ?? "1", 10));
  const limit = 20;
  const offset = (page - 1) * limit;

  const data = await adminApi
    .getUsers({
      search:    sp.search    || undefined,
      role:      sp.role      || undefined,
      plan:      sp.plan      || undefined,
      is_active: sp.is_active ? sp.is_active === "true" : undefined,
      limit,
      offset,
    })
    .catch(() => ({ items: [], total: 0 }));

  return (
    <AdminUsersClient
      initialData={data}
      page={page}
      limit={limit}
      initialSearch={sp.search ?? ""}
      initialRole={sp.role ?? ""}
      initialPlan={sp.plan ?? ""}
      initialStatus={sp.is_active ?? ""}
    />
  );
}
