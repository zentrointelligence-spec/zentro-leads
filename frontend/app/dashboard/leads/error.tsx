"use client";

/**
 * Route-level error surface when leads or stats fail to load from the API.
 */
export default function LeadsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto max-w-lg rounded-lg border border-red-500/20 bg-red-500/[0.06] px-8 py-10 text-center">
      <p className="text-[15px] font-semibold tracking-tight text-red-200/95">Could not load leads</p>
      <p className="mt-2 break-words text-[13px] leading-relaxed text-red-200/70">{error.message}</p>
      <button
        type="button"
        onClick={() => reset()}
        className="mt-8 h-10 rounded-md bg-zinc-100 px-5 text-[13px] font-medium text-zinc-900 transition-colors hover:bg-white"
      >
        Try again
      </button>
    </div>
  );
}
