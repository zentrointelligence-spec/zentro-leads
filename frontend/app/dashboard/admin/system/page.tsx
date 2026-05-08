import { adminApi, type SystemHealth } from "@/lib/api";
import { SystemHealthClient } from "./_components/system-health-client";

export const dynamic = "force-dynamic";

export default async function AdminSystemPage() {
  const health: SystemHealth | null = await adminApi.getSystemHealth().catch(() => null);
  return <SystemHealthClient initialHealth={health} />;
}
