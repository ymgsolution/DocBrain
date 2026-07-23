import { Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
import { ActivityFeedItem } from "@/components/shared/activity-feed-item";
import type { ActivityEvent } from "@/features/dashboard/types";

export function ActivityFeed({ events }: { events: ActivityEvent[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <EmptyState icon={Activity} title="No activity yet" description="Uploads and edits will show up here." />
        ) : (
          <div className="divide-border -my-1 divide-y">
            {events.map((event) => (
              <ActivityFeedItem key={event.id} event={event} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
