/**
 * Suspense-style skeleton for the leads dashboard route.
 */
export default function LeadsLoading() {
  return (
    <div className="mx-auto max-w-[1600px] space-y-10 animate-pulse pb-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6 lg:gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-[104px] rounded-lg border border-white/[0.05] bg-[#09090b]/60"
          />
        ))}
      </div>
      <div className="h-28 rounded-lg border border-white/[0.05] bg-[#09090b]/60" />
      <div className="h-48 rounded-lg border border-white/[0.05] bg-[#09090b]/60" />
      <div className="h-[420px] rounded-lg border border-white/[0.05] bg-[#09090b]/60" />
    </div>
  );
}
