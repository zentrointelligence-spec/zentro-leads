import type { ReactNode } from "react";
import { MarketingNav } from "./_components/nav";
import { MarketingFooter } from "./_components/footer";

export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#0B1120] text-white">
      <MarketingNav />
      {children}
      <MarketingFooter />
    </div>
  );
}
