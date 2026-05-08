import { adminApi, type ActivityEvent } from "@/lib/api";
import { AdminOverviewClient } from "./_components/admin-overview-client";

export const dynamic = "force-dynamic";

export default async function AdminOverviewPage() {
  const [stats, activity] = await Promise.all([
    adminApi.getStats().catch(() => null),
    adminApi.getActivity().catch(() => [] as ActivityEvent[]),
  ]);

  return <AdminOverviewClient initialStats={stats} initialActivity={activity} />;
}
