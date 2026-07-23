"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useCreateCategory, useUpdateCategory } from "@/features/taxonomy/hooks";
import { ApiError } from "@/lib/api-client";
import { applyApiFieldErrors } from "@/lib/form-errors";
import type { Category } from "@/features/taxonomy/types";

const categorySchema = z.object({
  name: z.string().min(1, "Name is required").max(200),
  description: z.string().max(1000).optional().or(z.literal("")),
  defaultReviewPeriodDays: z.string().optional().or(z.literal("")),
});

type CategoryValues = z.infer<typeof categorySchema>;

interface CategoryFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  category?: Category; // omitted = create mode
}

export function CategoryFormDialog({ open, onOpenChange, category }: CategoryFormDialogProps) {
  const isEditing = Boolean(category);
  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory(category?.id ?? "");
  const mutation = isEditing ? updateCategory : createCategory;

  const form = useForm<CategoryValues>({
    resolver: zodResolver(categorySchema),
    values: {
      name: category?.name ?? "",
      description: category?.description ?? "",
      defaultReviewPeriodDays: category?.defaultReviewPeriodDays ? String(category.defaultReviewPeriodDays) : "",
    },
  });

  function handleOpenChange(next: boolean) {
    if (mutation.isPending) return;
    if (!next) form.reset();
    onOpenChange(next);
  }

  function onSubmit(values: CategoryValues) {
    const payload = {
      name: values.name,
      description: values.description || undefined,
      defaultReviewPeriodDays: values.defaultReviewPeriodDays ? Number(values.defaultReviewPeriodDays) : undefined,
    };

    mutation.mutate(payload, {
      onSuccess: () => {
        toast.success(isEditing ? "Category updated" : "Category created");
        form.reset();
        onOpenChange(false);
      },
      onError: (error) => {
        if (applyApiFieldErrors(form, error)) return;
        toast.error(error instanceof ApiError ? error.message : "Couldn't save this category, try again.");
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit category" : "New category"}</DialogTitle>
          <DialogDescription>
            {isEditing ? "Update this category's details." : "Categories are required when uploading a document."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <fieldset disabled={mutation.isPending} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="category-name">Name</Label>
              <Input id="category-name" {...form.register("name")} />
              {form.formState.errors.name && (
                <p className="text-destructive text-xs">{form.formState.errors.name.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="category-description">Description</Label>
              <Textarea id="category-description" rows={2} placeholder="Optional" {...form.register("description")} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="category-review-period">Default review period (days)</Label>
              <Input
                id="category-review-period"
                type="number"
                min={1}
                placeholder="Optional — e.g. 180"
                {...form.register("defaultReviewPeriodDays")}
              />
            </div>
          </fieldset>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving…" : isEditing ? "Save" : "Create category"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
