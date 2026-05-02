import { Globe } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function LandingPagesPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6 animate-fade-in-up">
      <div>
        <h1 className="text-2xl font-bold text-foreground-primary">Landing Pages</h1>
        <p className="mt-0.5 text-sm text-foreground-secondary">
          Lead capture pages and conversion forms
        </p>
      </div>

      <Card className="py-16">
        <CardContent className="flex flex-col items-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-potential-light">
            <Globe className="h-7 w-7 text-potential" />
          </div>
          <h3 className="text-lg font-semibold text-foreground-primary">
            Landing Page Builder
          </h3>
          <p className="mt-2 max-w-md text-sm text-foreground-secondary">
            Create high-converting lead capture pages with AI-optimized copy and
            built-in form validation.
          </p>
          <Badge variant="potential" className="mt-6">
            Coming Soon
          </Badge>
        </CardContent>
      </Card>
    </div>
  );
}
