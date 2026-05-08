import { authApi, leadsApi, type LeadStatus, type LeadTier } from "@/lib/api";
import { parseLeadsQuery } from "@/lib/leads-url";

import { LeadIntelligenceDashboard } from "./components/lead-intelligence-dashboard";

export default async function LeadsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const user = await authApi.me();
  const sp = await searchParams;
  const q = parseLeadsQuery(sp);

  const tier = q.tier as LeadTier | undefined;
  const status = q.status as LeadStatus | undefined;

  const [paginated, stats] = await Promise.all([
    leadsApi.list({
      page: q.page,
      per_page: Math.min(q.per_page, 100),
      search: q.search,
      tier,
      status,
      has_email: q.has_email,
      zims_synced: q.zims_synced,
      min_icp_match: q.min_icp_match && q.min_icp_match > 0 ? q.min_icp_match : undefined,
      lead_type: q.lead_type,
      market:    q.market,
    }),
    leadsApi.stats(),
  ]);

  return (
    <LeadIntelligenceDashboard
      user={user}
      initialLeads={paginated.items}
      stats={stats}
      query={q}
      total={paginated.total}
      pages={paginated.pages}
    />
  );
}
