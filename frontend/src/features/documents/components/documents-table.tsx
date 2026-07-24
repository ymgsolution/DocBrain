"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { FileTypeIcon } from "@/components/shared/file-type-icon";
import { UserAvatar } from "@/components/shared/user-avatar";
import { ReviewStatusBadge } from "@/components/shared/status-badge";
import { getReviewStatus, formatRelativeTime } from "@/lib/format";
import type { DocumentSummary } from "@/types/document";

export function DocumentsTable({ documents }: { documents: DocumentSummary[] }) {
  const router = useRouter();

  return (
    <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
      <Table className="table-fixed">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-[32%]">Title</TableHead>
            <TableHead className="w-[14%]">Category</TableHead>
            <TableHead className="w-[18%]">Owner</TableHead>
            <TableHead className="w-[8%]">Version</TableHead>
            <TableHead className="w-[13%]">Review</TableHead>
            <TableHead className="w-[15%]">Updated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((document) => (
            <TableRow
              key={document.id}
              className="cursor-pointer"
              onClick={() => router.push(`/documents/${document.id}`)}
            >
              <TableCell>
                <div className="flex items-center gap-2.5">
                  <div className="bg-muted text-muted-foreground flex size-8 shrink-0 items-center justify-center rounded-md">
                    <FileTypeIcon
                      filename={document.currentVersion?.originalFilename ?? document.title}
                      className="size-4"
                    />
                  </div>
                  <div className="min-w-0">
                    <Link
                      href={`/documents/${document.id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="hover:text-primary block truncate text-sm font-medium"
                    >
                      {document.title}
                    </Link>
                    {document.description && (
                      <p className="text-muted-foreground truncate text-xs">{document.description}</p>
                    )}
                  </div>
                </div>
              </TableCell>
              <TableCell className="text-muted-foreground truncate text-sm">{document.category.name}</TableCell>
              <TableCell>
                <div className="flex min-w-0 items-center gap-2">
                  <UserAvatar name={document.owner.displayName} className="size-6 shrink-0" />
                  <span className="truncate text-sm">{document.owner.displayName}</span>
                </div>
              </TableCell>
              <TableCell className="text-muted-foreground text-sm tabular-nums">v{document.versionCount}</TableCell>
              <TableCell className="overflow-hidden">
                <ReviewStatusBadge status={getReviewStatus(document.reviewDueDate)} />
              </TableCell>
              <TableCell className="text-muted-foreground truncate text-sm">{formatRelativeTime(document.updatedAt)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
