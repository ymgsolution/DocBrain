import { FileStack } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { DownloadLink } from "@/components/shared/download-link";
import { Skeleton } from "@/components/ui/skeleton";
import { formatFileSize, formatRelativeTime } from "@/lib/format";
import { ApiError } from "@/lib/api-client";
import { useDocumentVersions } from "@/features/documents/hooks";

export function VersionsTab({ documentId }: { documentId: string }) {
  const { data: versions, isLoading, isError, error, refetch } = useDocumentVersions(documentId);

  if (isError) {
    return (
      <ErrorState
        message={error instanceof ApiError ? error.message : "Couldn't load version history."}
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
                <DownloadLink
                  documentId={documentId}
                  versionNumber={version.versionNumber}
                  filename={version.originalFilename}
                  variant="ghost"
                  size="icon-sm"
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
