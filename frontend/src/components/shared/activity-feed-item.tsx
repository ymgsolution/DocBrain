import { UserAvatar } from "@/components/shared/user-avatar";
import { formatRelativeTime } from "@/lib/format";
import type { ActivityEvent } from "@/features/dashboard/types";

export function ActivityFeedItem({ event }: { event: ActivityEvent }) {
  return (
    <div className="flex items-start gap-3 px-2 py-2">
      <UserAvatar name={event.actorName} className="mt-0.5 size-7" />
      <div className="min-w-0 flex-1">
        <p className="text-sm">{event.summary}</p>
        <p className="text-muted-foreground mt-0.5 text-xs">{formatRelativeTime(event.occurredAt)}</p>
      </div>
    </div>
  );
}
