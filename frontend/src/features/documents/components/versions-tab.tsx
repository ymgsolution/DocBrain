"use client";

import { useState } from "react";
import { toast } from "sonner";
import { FileStack, RotateCcw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { DownloadLink } from "@/components/shared/download-link";
import { Skeleton } from "@/components/ui/skeleton";
import { formatFileSize, formatRelativeTime } from "@/lib/format";
import { ApiError } from "@/lib/api-client";
import { useDocumentVersions, useRestoreVersion } from "@/features/documents/hooks";
import type { VersionDetail } from "@/types/document";

interface VersionsTabProps {
  documentId: string;
  canManageVersions: boolean;
}

export function VersionsTab({ documentId, canManageVersions }: VersionsTabProps) {
  const { data: versions, isLoading, isError, error, refetch } = useDocumentVersions(documentId);
  const restoreVersion = useRestoreVersion(documentId);
  const [restoreTarget, setRestoreTarget] = useState<VersionDetail | null>(null);

  if (isError) {
    return (
      <ErrorState
        message={error instanceof ApiError ? error.message : "Couldn't load version history."}
        correlationId={error instanceof ApiError ? error.correlationId : undefined}
        onRetry={() => refetch()}
      />
    );
  }

  if (isLoading || !versions) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }, (_, i) => (
          <Skeleton key={i} className="h-12 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (versions.length === 0) {
    return <EmptyState icon={FileStack} title="No versions yet" />;
  }

  const sorted = [...versions].sort((a, b) => b.versionNumber - a.versionNumber);
  const currentVersion = sorted.find((v) => v.isCurrent);

  function handleConfirmRestore() {
    if (!restoreTarget) return;
    restoreVersion.mutate(restoreTarget.versionNumber, {
      onSuccess: (newVersion) => {
        toast.success(`Version ${restoreTarget.versionNumber} restored as version ${newVersion.versionNumber}`);
        setRestoreTarget(null);
      },
      onError: (error) => {
        // A 409 here means someone else uploaded/restored a version between
        // this tab loading and the restore click — the version list this
        // dialog was built from is now stale, so offer a way to fix that
        // directly rather than a bare error (§16.5's 409 row: a resolution
        // path, not just a message). Previously this branch was inverted —
        // it fired on non-ApiError (network failure) instead of the real
        // conflict case, so a genuine 409 fell through to a plain toast.
        if (error instanceof ApiError && error.status === 409) {
          toast.error("Someone uploaded a new version while you were viewing this.", {
            action: { label: "Refresh", onClick: () => refetch() },
          });
        } else {
          toast.error(error instanceof ApiError ? error.message : "Couldn't restore this version, try again.");
        }
        setRestoreTarget(null);
      },
    });
  }

  return (
    <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Version</TableHead>
            <TableHead>Uploaded by</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Change note</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((version) => (
            <TableRow key={version.id}>
              <TableCell className="font-medium">
                <div className="flex items-center gap-2">
                  v{version.versionNumber}
                  {version.isCurrent && <Badge className="font-normal">Current</Badge>}
                </div>
              </TableCell>
              <TableCell className="text-muted-foreground">{version.uploadedBy.displayName}</TableCell>
              <TableCell className="text-muted-foreground">{formatRelativeTime(version.uploadedAt)}</TableCell>
              <TableCell className="text-muted-foreground">{formatFileSize(version.sizeBytes)}</TableCell>
              <TableCell className="text-muted-foreground max-w-xs truncate">
                {version.changeNote ?? "—"}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-1">
                  <DownloadLink
                    documentId={documentId}
                    versionNumber={version.versionNumber}
                    filename={version.originalFilename}
                    variant="ghost"
                    size="icon-sm"
                  />
                  {canManageVersions && !version.isCurrent && (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`Restore version ${version.versionNumber}`}
                      onClick={() => setRestoreTarget(version)}
                    >
                      <RotateCcw className="size-4" />
                    </Button>
                  )}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {restoreTarget && currentVersion && (
        <ConfirmDialog
          open
          onOpenChange={(open) => !open && setRestoreTarget(null)}
          title={`Restore version ${restoreTarget.versionNumber}?`}
          description={`This creates a new version using version ${restoreTarget.versionNumber}'s content and replaces version ${currentVersion.versionNumber} as current. Version ${currentVersion.versionNumber} stays in history.`}
          confirmLabel="Restore"
          loading={restoreVersion.isPending}
          onConfirm={handleConfirmRestore}
        />
      )}
    </div>
  );
}
