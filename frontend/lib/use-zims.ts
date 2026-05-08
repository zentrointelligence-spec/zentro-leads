"use client";

import { useEffect, useState } from "react";

/**
 * Returns whether the current user has ZIMS connected.
 * Reads from the API once per session; falls back to false on any error.
 * Lightweight — no TanStack Query dependency needed for a simple flag.
 */
export function useZimsConnected(): { zimsConnected: boolean; loading: boolean } {
  const [zimsConnected, setZimsConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/v1/settings/integrations", { credentials: "include" })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (!cancelled) setZimsConnected(Boolean(data?.zims_linked));
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return { zimsConnected, loading };
}
