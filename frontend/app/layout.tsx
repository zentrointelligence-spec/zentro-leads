"use client";

import "./globals.css";
import { Inter } from "next/font/google";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { useState } from "react";

const inter = Inter({ subsets: ["latin"], variable: "--font-geist-sans" });

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
        <title>Zentro Leads — AI Lead Generation</title>
        <meta name="description" content="AI-powered B2B lead generation platform" />
      </head>
      <body className={`${inter.variable} font-sans antialiased`}>
        <QueryClientProvider client={queryClient}>
          {children}
          <Toaster richColors position="top-right" />
        </QueryClientProvider>
      </body>
    </html>
  );
}
