import Link from "next/link";
import { ClipboardCheck } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function PendingReviewsBanner({ count }: { count: number }) {
  if (count === 0) return null;

  return (
    <Card className="border-warning/30 bg-warning/5">
      <CardContent className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-warning/10 text-warning flex size-9 shrink-0 items-center justify-center rounded-lg">
            <ClipboardCheck className="size-4" />
          </div>
          <p className="text-sm">
            <span className="font-medium">{count}</span> {count === 1 ? "document needs" : "documents need"} review
            within the next 30 days.
          </p>
        </div>
        <Button variant="outline" size="sm" nativeButton={false} render={<Link href="/reviews" />}>
          Review now
        </Button>
      </CardContent>
    </Card>
  );
}
