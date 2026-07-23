import { Badge } from "@/components/ui/badge";
import { UserAvatar } from "@/components/shared/user-avatar";
import { ReviewStatusBadge } from "@/components/shared/status-badge";
import { getReviewStatus, formatRelativeTime } from "@/lib/format";
import type { DocumentDetail } from "@/types/document";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">{label}</p>
      <div className="mt-1 text-sm">{children}</div>
    </div>
  );
}

export function MetadataPanel({ document }: { document: DocumentDetail }) {
  return (
    <div className="space-y-4">
      <Field label="Category">{document.category.name}</Field>

      <Field label="Tags">
        {document.tags.length === 0 ? (
          <span className="text-muted-foreground">No tags</span>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {document.tags.map((tag) => (
              <Badge key={tag.id} variant="secondary">
                {tag.name}
              </Badge>
            ))}
          </div>
        )}
      </Field>

      <Field label="Owner">
        <div className="flex items-center gap-2">
          <UserAvatar name={document.owner.displayName} className="size-6" />
          {document.owner.displayName}
        </div>
      </Field>

      <Field label="Review status">
        <div className="flex items-center gap-2">
          <ReviewStatusBadge status={getReviewStatus(document.reviewDueDate)} />
          {document.reviewDueDate && <span className="text-muted-foreground">due {document.reviewDueDate}</span>}
        </div>
      </Field>

      {document.lastReviewedAt && (
        <Field label="Last reviewed">{formatRelativeTime(document.lastReviewedAt)}</Field>
      )}

      <Field label="Created">{formatRelativeTime(document.createdAt)}</Field>
      <Field label="Updated">{formatRelativeTime(document.updatedAt)}</Field>
    </div>
  );
}
