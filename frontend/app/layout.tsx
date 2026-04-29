"use client";

import "./globals.css";
import { Inter } from "next/font/google";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { AppToaster } from "./app-toaster";
import { ThemeProvider } from "./providers/theme-provider";

const inter = Inter({ subsets: ["latin"], variable: "--font-geist-sans" });

const themeInitScript = `(function(){try{var k='zentro-theme',s=localStorage.getItem(k);if(s==='dark'||s==='light'){document.documentElement.classList.toggle('dark',s==='dark');document.documentElement.style.colorScheme=s==='dark'?'dark':'light';return;}if(window.matchMedia('(prefers-color-scheme: dark)').matches){document.documentElement.classList.add('dark');document.documentElement.style.colorScheme='dark';}else{document.documentElement.style.colorScheme='light';}}catch(e){}})();`;

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
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body
        className={`${inter.variable} font-sans antialiased min-h-screen transition-colors duration-300`}
      >
        <QueryClientProvider client={queryClient}>
          <ThemeProvider>
            {children}
            <AppToaster />
          </ThemeProvider>
        </QueryClientProvider>
      </body>
    </html>
  );
}
