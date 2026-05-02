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
    <div className="mx-auto max-w-lg rounded-lg border border-hot/20 bg-hot-light px-8 py-10 text-center">
      <p className="text-[15px] font-semibold tracking-tight text-hot">
        Could not load leads
      </p>
      <p className="mt-2 break-words text-[13px] leading-relaxed text-foreground-secondary">
        {error.message}
      </p>
      <button
        type="button"
        onClick={() => reset()}
        className="mt-8 h-10 rounded-md bg-primary px-5 text-[13px] font-medium text-white transition-colors hover:bg-primary-dark"
      >
        Try again
      </button>
    </div>
  );
}
