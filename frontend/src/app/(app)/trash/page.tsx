"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Trash2, Undo2 } from "lucide-react";
import { AppBreadcrumb } from "@/components/layout/app-breadcrumb";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PaginationBar } from "@/components/shared/pagination-bar";
import { TypeToConfirmDialog } from "@/components/shared/type-to-confirm-dialog";
import { UserAvatar } from "@/components/shared/user-avatar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCurrentUser } from "@/features/auth/hooks";
import { useTrash } from "@/features/trash/hooks";
import { useHardDeleteDocument, useRestoreDocument } from "@/features/documents/hooks";
import { formatRelativeTime } from "@/lib/format";
import { ApiError } from "@/lib/api-client";
import type { TrashedDocumentItem } from "@/features/trash/types";

const PAGE_SIZE = 25;

export default function TrashPage() {
  const { data: user } = useCurrentUser();
  const isAdmin = user?.role === "ADMIN";

  const [page, setPage] = useState(0);
  const [deleteTarget, setDeleteTarget] = useState<TrashedDocumentItem | null>(null);
  const filters = useMemo(() => ({ page, size: PAGE_SIZE }), [page]);
  const { data, isLoading, isError, error, refetch } = useTrash(filters);
  const hardDelete = useHardDeleteDocument(deleteTarget?.id ?? "");

  function handleConfirmDelete() {
    if (!deleteTarget) return;
    hardDelete.mutate(undefined, {
      onSuccess: () => {
        toast.success(`"${deleteTarget.title}" permanently deleted`);
        setDeleteTarget(null);
      },
      onError: (error) => {
        toast.error(error instanceof ApiError ? error.message : "Couldn't delete this document, try again.");
        setDeleteTarget(null);
      },
    });
  }

  return (
    <div className="space-y-6">
      <AppBreadcrumb segments={[{ label: "Trash" }]} />
      <PageHeader
        title="Trash"
        description={
          isAdmin
            ? "Deleted documents across the organization. Restore or permanently delete."
            : "Documents you've deleted. Restore them any time."
        }
      />

      {isError ? (
        <ErrorState
          message={error instanceof ApiError ? error.message : "Couldn't load Trash."}
          correlationId={error instanceof ApiError ? error.correlationId : undefined}
          onRetry={() => refetch()}
        />
      ) : isLoading || !data ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-14 w-full rounded-lg" />
          ))}
        </div>
      ) : data.items.length === 0 ? (
        <EmptyState icon={Trash2} title="Trash is empty." />
      ) : (
        <>
          <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Title</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead>Deleted by</TableHead>
                  <TableHead>Deleted</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((item) => (
                  <TrashRow key={item.id} item={item} isAdmin={isAdmin} onDeletePermanently={() => setDeleteTarget(item)} />
                ))}
              </TableBody>
            </Table>
          </div>
          <PaginationBar
            page={data.page}
            size={data.size}
            total={data.total}
            totalPages={data.totalPages}
            onPageChange={setPage}
          />
        </>
      )}

      <TypeToConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete permanently?"
        description={`“${deleteTarget?.title}” and all of its versions will be permanently deleted. This can't be undone.`}
        confirmText={deleteTarget?.title ?? ""}
        loading={hardDelete.isPending}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}

function TrashRow({
  item,
  isAdmin,
  onDeletePermanently,
}: {
  item: TrashedDocumentItem;
  isAdmin: boolean;
  onDeletePermanently: () => void;
}) {
  const restore = useRestoreDocument(item.id);

  function handleRestore() {
    restore.mutate(undefined, {
      onSuccess: () => toast.success(`"${item.title}" restored`),
      onError: (error) => {
        toast.error(error instanceof ApiError ? error.message : "Couldn't restore this document, try again.");
      },
    });
  }

  return (
    <TableRow>
      <TableCell className="max-w-xs truncate text-sm font-medium">
        <Link href={`/documents/${item.id}`} className="hover:text-primary">
          {item.title}
        </Link>
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">{item.category.name}</TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <UserAvatar name={item.owner.displayName} className="size-6" />
          <span className="text-sm">{item.owner.displayName}</span>
        </div>
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">{item.deletedBy?.displayName ?? "—"}</TableCell>
      <TableCell className="text-muted-foreground text-sm">{formatRelativeTime(item.deletedAt)}</TableCell>
      <TableCell className="text-right">
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" className="gap-1.5" onClick={handleRestore} disabled={restore.isPending}>
            <Undo2 className="size-3.5" />
            Restore
          </Button>
          {isAdmin && (
            <Button variant="ghost" size="icon-sm" aria-label={`Delete ${item.title} permanently`} onClick={onDeletePermanently}>
              <Trash2 className="size-4" />
            </Button>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}
