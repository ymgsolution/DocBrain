import { Activity } from "lucide-react";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { ActivityFeedItem } from "@/components/shared/activity-feed-item";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client";
import { useDocumentActivity } from "@/features/documents/hooks";

export function DocumentActivityTab({ documentId }: { documentId: string }) {
  const { data, isLoading, isError, error, refetch } = useDocumentActivity(documentId);

  if (isError) {
    return (
      <ErrorState
        message={error instanceof ApiError ? error.message : "Couldn't load activity."}
        correlationId={error instanceof ApiError ? error.correlationId : undefined}
        onRetry={() => refetch()}
      />
    );
  }

  if (isLoading || !data) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }, (_, i) => (
          <Skeleton key={i} className="h-12 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (data.items.length === 0) {
    return <EmptyState icon={Activity} title="No activity yet" />;
  }

  return (
    <div className="divide-border divide-y rounded-xl ring-1 ring-foreground/10">
      {data.items.map((event) => (
        <ActivityFeedItem key={event.id} event={event} />
      ))}
    </div>
  );
}
