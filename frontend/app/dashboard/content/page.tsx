import { FileText } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function ContentPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6 animate-fade-in-up">
      <div>
        <h1 className="text-2xl font-bold text-foreground-primary">Content</h1>
        <p className="mt-0.5 text-sm text-foreground-secondary">
          AI-generated sales content and email templates
        </p>
      </div>

      <Card className="py-16">
        <CardContent className="flex flex-col items-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-primary-light">
            <FileText className="h-7 w-7 text-primary" />
          </div>
          <h3 className="text-lg font-semibold text-foreground-primary">
            AI Content Generator
          </h3>
          <p className="mt-2 max-w-md text-sm text-foreground-secondary">
            Generate personalized outreach emails, LinkedIn messages, and WhatsApp
            templates tailored to each lead.
          </p>
          <Badge variant="primary" className="mt-6">
            Coming Soon
          </Badge>
        </CardContent>
      </Card>
    </div>
  );
}
