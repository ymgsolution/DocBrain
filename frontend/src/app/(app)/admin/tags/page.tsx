"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Tag as TagIcon, Pencil, GitMerge, Trash2 } from "lucide-react";
import { AppBreadcrumb } from "@/components/layout/app-breadcrumb";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { ForbiddenState } from "@/components/shared/forbidden-state";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useCurrentUser } from "@/features/auth/hooks";
import { useTags, useDeleteTag } from "@/features/taxonomy/hooks";
import { RenameTagDialog } from "@/features/taxonomy/components/rename-tag-dialog";
import { MergeTagDialog } from "@/features/taxonomy/components/merge-tag-dialog";
import { ApiError } from "@/lib/api-client";
import type { Tag } from "@/features/taxonomy/types";

export default function TagsAdminPage() {
  const { data: user, isLoading: userLoading } = useCurrentUser();
  const { data: tags, isLoading, isError, error, refetch } = useTags();
  const deleteTag = useDeleteTag();

  const [renameTarget, setRenameTarget] = useState<Tag | null>(null);
  const [mergeTarget, setMergeTarget] = useState<Tag | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Tag | null>(null);

  if (userLoading) {
    return <Skeleton className="h-64 w-full rounded-lg" />;
  }

  if (user && user.role !== "ADMIN") {
    return (
      <div className="space-y-6">
        <AppBreadcrumb segments={[{ label: "Tags" }]} />
        <ForbiddenState requiredRole="Admin" />
      </div>
    );
  }

  function handleConfirmDelete() {
    if (!deleteTarget) return;
    deleteTag.mutate(deleteTarget.id, {
      onSuccess: () => {
        toast.success(`"${deleteTarget.name}" deleted`);
        setDeleteTarget(null);
      },
      onError: (error) => {
        toast.error(error instanceof ApiError ? error.message : "Couldn't delete this tag, try again.");
        setDeleteTarget(null);
      },
    });
  }

  return (
    <div className="space-y-6">
      <AppBreadcrumb segments={[{ label: "Tags" }]} />
      <PageHeader title="Tags" description="Sorted by usage. Created automatically when documents are tagged." />

      {isError ? (
        <ErrorState
          message={error instanceof ApiError ? error.message : "Couldn't load tags."}
          onRetry={() => refetch()}
        />
      ) : isLoading || !tags ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      ) : tags.length === 0 ? (
        <EmptyState icon={TagIcon} title="No tags yet" description="Tags appear here once documents are tagged." />
      ) : (
        <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Name</TableHead>
                <TableHead>Usage</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tags.map((tag) => {
                const inUse = tag.usageCount > 0;
                return (
                  <TableRow key={tag.id}>
                    <TableCell className="font-medium">{tag.name}</TableCell>
                    <TableCell className="text-muted-foreground tabular-nums">{tag.usageCount}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon-sm" aria-label={`Rename ${tag.name}`} onClick={() => setRenameTarget(tag)}>
                          <Pencil className="size-4" />
                        </Button>
                        <Button variant="ghost" size="icon-sm" aria-label={`Merge ${tag.name}`} onClick={() => setMergeTarget(tag)}>
                          <GitMerge className="size-4" />
                        </Button>
                        {inUse ? (
                          <Tooltip>
                            <TooltipTrigger render={<span tabIndex={0} />}>
                              <Button variant="ghost" size="icon-sm" aria-label={`Delete ${tag.name}`} disabled>
                                <Trash2 className="size-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Used by {tag.usageCount} document(s) — merge instead</TooltipContent>
                          </Tooltip>
                        ) : (
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={`Delete ${tag.name}`}
                            onClick={() => setDeleteTarget(tag)}
                          >
                            <Trash2 className="size-4" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <RenameTagDialog tag={renameTarget} onOpenChange={(open) => !open && setRenameTarget(null)} />
      <MergeTagDialog tag={mergeTarget} onOpenChange={(open) => !open && setMergeTarget(null)} />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete tag?"
        description={`“${deleteTarget?.name}” will be permanently deleted. This can't be undone.`}
        confirmLabel="Delete"
        destructive
        loading={deleteTag.isPending}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
