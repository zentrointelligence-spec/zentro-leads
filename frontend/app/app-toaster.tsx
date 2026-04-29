"use client";

import { Toaster } from "sonner";

import { useTheme } from "./providers/theme-provider";

/**
 * Sonner wired to app theme (light/dark).
 */
export function AppToaster() {
  const { theme, mounted } = useTheme();
  return (
    <Toaster
      richColors
      position="top-right"
      theme={mounted ? theme : "system"}
      toastOptions={{
        classNames: {
          toast:
            "backdrop-blur-md border border-[color:var(--border-color)] bg-[color:var(--card-bg)] text-[color:var(--text-primary)] shadow-lg",
        },
      }}
    />
  );
}
