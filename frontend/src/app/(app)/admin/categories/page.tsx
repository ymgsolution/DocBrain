"use client";

import { useState } from "react";
import { toast } from "sonner";
import { FolderTree, Plus, Pencil, Archive, ArchiveRestore, Trash2 } from "lucide-react";
import { AppBreadcrumb } from "@/components/layout/app-breadcrumb";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { ForbiddenState } from "@/components/shared/forbidden-state";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useCurrentUser } from "@/features/auth/hooks";
import { useCategories, useUpdateCategory, useDeleteCategory } from "@/features/taxonomy/hooks";
import { CategoryFormDialog } from "@/features/taxonomy/components/category-form-dialog";
import { ApiError } from "@/lib/api-client";
import type { Category } from "@/features/taxonomy/types";

export default function CategoriesAdminPage() {
  const { data: user, isLoading: userLoading } = useCurrentUser();
  const { data: categories, isLoading, isError, error, refetch } = useCategories(true);
  const deleteCategory = useDeleteCategory();

  const [formOpen, setFormOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | undefined>(undefined);
  const [deleteTarget, setDeleteTarget] = useState<Category | null>(null);

  if (userLoading) {
    return <Skeleton className="h-64 w-full rounded-lg" />;
  }

  if (user && user.role !== "ADMIN") {
    return (
      <div className="space-y-6">
        <AppBreadcrumb segments={[{ label: "Categories" }]} />
        <ForbiddenState requiredRole="Admin" />
      </div>
    );
  }

  function openCreate() {
    setEditingCategory(undefined);
    setFormOpen(true);
  }

  function openEdit(category: Category) {
    setEditingCategory(category);
    setFormOpen(true);
  }

  function handleConfirmDelete() {
    if (!deleteTarget) return;
    deleteCategory.mutate(deleteTarget.id, {
      onSuccess: () => {
        toast.success(`"${deleteTarget.name}" deleted`);
        setDeleteTarget(null);
      },
      onError: (error) => {
        toast.error(error instanceof ApiError ? error.message : "Couldn't delete this category, try again.");
        setDeleteTarget(null);
      },
    });
  }

  return (
    <div className="space-y-6">
      <AppBreadcrumb segments={[{ label: "Categories" }]} />
      <PageHeader
        title="Categories"
        description="The controlled vocabulary documents are organized under."
        actions={
          <Button size="sm" className="gap-1.5" onClick={openCreate}>
            <Plus className="size-4" />
            New Category
          </Button>
        }
      />

      {isError ? (
        <ErrorState
          message={error instanceof ApiError ? error.message : "Couldn't load categories."}
          onRetry={() => refetch()}
        />
      ) : isLoading || !categories ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      ) : categories.length === 0 ? (
        <EmptyState icon={FolderTree} title="No categories yet" action={<Button onClick={openCreate}>New Category</Button>} />
      ) : (
        <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Name</TableHead>
                <TableHead className="hidden md:table-cell">Description</TableHead>
                <TableHead>Usage</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {categories.map((category) => (
                <CategoryRow
                  key={category.id}
                  category={category}
                  onEdit={() => openEdit(category)}
                  onDelete={() => setDeleteTarget(category)}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <CategoryFormDialog open={formOpen} onOpenChange={setFormOpen} category={editingCategory} />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete category?"
        description={`“${deleteTarget?.name}” will be permanently deleted. This can't be undone.`}
        confirmLabel="Delete"
        destructive
        loading={deleteCategory.isPending}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}

function CategoryRow({ category, onEdit, onDelete }: { category: Category; onEdit: () => void; onDelete: () => void }) {
  const updateCategory = useUpdateCategory(category.id);
  const inUse = category.documentCount > 0;

  function toggleArchived() {
    updateCategory.mutate(
      { isArchived: !category.isArchived },
      {
        onSuccess: () => {
          toast.success(category.isArchived ? `"${category.name}" unarchived` : `"${category.name}" archived`);
        },
        onError: (error) => {
          toast.error(error instanceof ApiError ? error.message : "Couldn't update this category, try again.");
        },
      },
    );
  }

  return (
    <TableRow>
      <TableCell className="font-medium">{category.name}</TableCell>
      <TableCell className="text-muted-foreground hidden max-w-xs truncate md:table-cell">
        {category.description ?? "—"}
      </TableCell>
      <TableCell className="text-muted-foreground tabular-nums">{category.documentCount}</TableCell>
      <TableCell>
        <Badge variant={category.isArchived ? "secondary" : "outline"} className="font-normal">
          {category.isArchived ? "Archived" : "Active"}
        </Badge>
      </TableCell>
      <TableCell className="text-right">
        <div className="flex justify-end gap-1">
          <Button variant="ghost" size="icon-sm" aria-label={`Edit ${category.name}`} onClick={onEdit}>
            <Pencil className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={category.isArchived ? `Unarchive ${category.name}` : `Archive ${category.name}`}
            onClick={toggleArchived}
            disabled={updateCategory.isPending}
          >
            {category.isArchived ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
          </Button>
          {inUse ? (
            <Tooltip>
              <TooltipTrigger render={<span tabIndex={0} />}>
                <Button variant="ghost" size="icon-sm" aria-label={`Delete ${category.name}`} disabled>
                  <Trash2 className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Used by {category.documentCount} document(s) — archive instead</TooltipContent>
            </Tooltip>
          ) : (
            <Button variant="ghost" size="icon-sm" aria-label={`Delete ${category.name}`} onClick={onDelete}>
              <Trash2 className="size-4" />
            </Button>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}
