"use client";

import "./globals.css";
import { Inter } from "next/font/google";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { AppToaster } from "./app-toaster";
import { ThemeProvider } from "./providers/theme-provider";
import { ParticleField } from "@/components/ui/particle-field";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

const themeInitScript = `(function(){try{var k='zentro-theme',s=localStorage.getItem(k);var t=s==='dark'||s==='light'?s:(window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.classList.toggle('dark',t==='dark');document.documentElement.style.colorScheme=t==='dark'?'dark':'light';}catch(e){}})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 60 * 1000, retry: 1 },
        },
      })
  );

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <title>LeadRadar — AI Lead Generation</title>
        <meta name="description" content="AI-powered B2B lead generation platform" />
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body
        className={`${inter.variable} font-sans antialiased min-h-screen transition-colors duration-300`}
      >
        <QueryClientProvider client={queryClient}>
          <ThemeProvider>
            <ParticleField />
            {children}
            <AppToaster />
          </ThemeProvider>
        </QueryClientProvider>
      </body>
    </html>
  );
}
