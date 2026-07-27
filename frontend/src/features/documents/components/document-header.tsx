import { ClipboardCheck, FilePlus2, Loader2, Pencil, Share2, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileTypeIcon } from "@/components/shared/file-type-icon";
import { ReviewStatusBadge } from "@/components/shared/status-badge";
import { DownloadLink } from "@/components/shared/download-link";
import { getReviewStatus, isExtractionPending, isAiSuggestionPending } from "@/lib/format";
import type { DocumentDetail } from "@/types/document";
import type { UserSummary } from "@/features/auth/types";

interface DocumentHeaderProps {
  document: DocumentDetail;
  currentUser: UserSummary;
  editing: boolean;
  onEdit: () => void;
  onDelete: () => void;
  onMarkReviewed: () => void;
  onUploadVersion: () => void;
  onShare: () => void;
}

export function DocumentHeader({
  document,
  currentUser,
  editing,
  onEdit,
  onDelete,
  onMarkReviewed,
  onUploadVersion,
  onShare,
}: DocumentHeaderProps) {
  const canEdit = document.owner.id === currentUser.id || currentUser.role === "REVIEWER" || currentUser.role === "ADMIN";
  const canDelete = document.owner.id === currentUser.id || currentUser.role === "ADMIN";
  const canMarkReviewed = currentUser.role === "REVIEWER" || currentUser.role === "ADMIN";

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex min-w-0 items-start gap-3">
        <div className="bg-muted text-muted-foreground mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-lg">
          <FileTypeIcon filename={document.currentVersion?.originalFilename ?? document.title} className="size-5" />
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight text-balance">{document.title}</h1>
            {document.currentVersion && (
              <span className="text-muted-foreground bg-muted rounded-full px-2 py-0.5 text-xs font-medium">
                v{document.versionCount}
              </span>
            )}
            <ReviewStatusBadge status={getReviewStatus(document.reviewDueDate)} />
            {/* AI feature track — quiet, self-clearing; no error state shown
                for FAILED/UNSUPPORTED, matching the app's graceful-degradation
                pattern for background AI work (nothing to act on, so nothing
                shown). Both timeouts happen automatically after a couple of
                minutes, so this never spins forever if the worker is down or
                a job is stuck. Two distinct phases, not one generic spinner —
                extraction finishing but Gemini still running is a real gap
                (seconds, not instant) that otherwise looks like nothing is
                happening at all. */}
            {isExtractionPending(document) ? (
              <Badge variant="outline" className="gap-1 font-normal">
                <Loader2 className="size-3 animate-spin" />
                Analyzing document…
              </Badge>
            ) : (
              isAiSuggestionPending(document) && (
                <Badge variant="outline" className="gap-1 font-normal">
                  <Loader2 className="size-3 animate-spin" />
                  Getting AI suggestions…
                </Badge>
              )
            )}
          </div>
          {document.description && <p className="text-muted-foreground mt-1 text-sm">{document.description}</p>}
        </div>
      </div>

      {!editing && (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {document.currentVersion && (
            <DownloadLink
              documentId={document.id}
              versionNumber={document.currentVersion.versionNumber}
              filename={document.currentVersion.originalFilename}
            />
          )}
          {canEdit && (
            <Button variant="outline" size="sm" className="gap-1.5" onClick={onShare}>
              <Share2 className="size-4" />
              Share
            </Button>
          )}
          {canEdit && (
            <Button variant="outline" size="sm" className="gap-1.5" onClick={onUploadVersion}>
              <FilePlus2 className="size-4" />
              Upload new version
            </Button>
          )}
          {canMarkReviewed && (
            <Button variant="outline" size="sm" className="gap-1.5" onClick={onMarkReviewed}>
              <ClipboardCheck className="size-4" />
              Mark as reviewed
            </Button>
          )}
          {canEdit && (
            <Button variant="outline" size="sm" className="gap-1.5" onClick={onEdit}>
              <Pencil className="size-4" />
              Edit
            </Button>
          )}
          {canDelete && (
            <Button variant="outline" size="sm" className="text-destructive gap-1.5" onClick={onDelete}>
              <Trash2 className="size-4" />
              Delete
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
