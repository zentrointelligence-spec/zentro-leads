/**
 * Suspense-style skeleton for the leads dashboard route.
 */
export default function LeadsLoading() {
  return (
    <div className="mx-auto max-w-[1600px] space-y-6 animate-pulse pb-4">
      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-20 rounded-lg border border-border bg-background-secondary"
          />
        ))}
      </div>
      {/* Toolbar */}
      <div className="h-10 rounded-lg border border-border bg-background-secondary" />
      {/* Kanban columns */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-[420px] rounded-lg border border-border bg-background-secondary" />
        ))}
      </div>
    </div>
  );
}
