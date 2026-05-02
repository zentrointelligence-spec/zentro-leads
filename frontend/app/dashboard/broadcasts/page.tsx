import { Megaphone } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function BroadcastsPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6 animate-fade-in-up">
      <div>
        <h1 className="text-2xl font-bold text-foreground-primary">Broadcasts</h1>
        <p className="mt-0.5 text-sm text-foreground-secondary">
          WhatsApp and email broadcast campaigns
        </p>
      </div>

      <Card className="py-16">
        <CardContent className="flex flex-col items-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-warm-light">
            <Megaphone className="h-7 w-7 text-warm" />
          </div>
          <h3 className="text-lg font-semibold text-foreground-primary">
            Broadcast Campaigns
          </h3>
          <p className="mt-2 max-w-md text-sm text-foreground-secondary">
            Send bulk WhatsApp messages and email campaigns to segmented lead
            lists with delivery tracking.
          </p>
          <Badge variant="warm" className="mt-6">
            Coming Soon
          </Badge>
        </CardContent>
      </Card>
    </div>
  );
}
