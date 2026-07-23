import { DocumentListItem } from "@/components/shared/document-list-item";
import { ReviewStatusBadge } from "@/components/shared/status-badge";
import { getReviewStatus, formatRelativeTime } from "@/lib/format";
import type { DocumentSummary } from "@/types/document";

export function DocumentsMobileList({ documents }: { documents: DocumentSummary[] }) {
  return (
    <div className="divide-border divide-y rounded-xl ring-1 ring-foreground/10">
      {documents.map((document) => (
        <DocumentListItem
          key={document.id}
          document={document}
          meta={`${document.category.name} · ${formatRelativeTime(document.updatedAt)}`}
          trailing={<ReviewStatusBadge status={getReviewStatus(document.reviewDueDate)} />}
        />
      ))}
    </div>
  );
}
