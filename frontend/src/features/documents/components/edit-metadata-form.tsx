"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, Controller } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TagInput } from "@/features/documents/components/tag-input";
import { useCategories } from "@/features/taxonomy/hooks";
import { useUpdateDocument } from "@/features/documents/hooks";
import { ApiError } from "@/lib/api-client";
import { applyApiFieldErrors } from "@/lib/form-errors";
import type { DocumentDetail } from "@/types/document";

const editSchema = z.object({
  title: z.string().min(3, "Title must be at least 3 characters").max(200),
  categoryId: z.string().min(1, "Category is required"),
  description: z.string().max(1000).optional().or(z.literal("")),
  reviewDueDate: z.string().optional().or(z.literal("")),
});

type EditValues = z.infer<typeof editSchema>;

interface EditMetadataFormProps {
  document: DocumentDetail;
  onDone: () => void;
}

export function EditMetadataForm({ document, onDone }: EditMetadataFormProps) {
  const { data: categories } = useCategories();
  const updateDocument = useUpdateDocument(document.id);
  const [tags, setTags] = useState<string[]>(document.tags.map((t) => t.name));

  const form = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      title: document.title,
      categoryId: document.category.id,
      description: document.description ?? "",
      reviewDueDate: document.reviewDueDate ?? "",
    },
  });

  const categoryLabels: Record<string, string> = {};
  categories?.forEach((c) => (categoryLabels[c.id] = c.name));

  function onSubmit(values: EditValues) {
    updateDocument.mutate(
      {
        title: values.title,
        categoryId: values.categoryId,
        description: values.description || undefined,
        reviewDueDate: values.reviewDueDate || null,
        tags,
      },
      {
        onSuccess: () => {
          toast.success("Details updated");
          onDone();
        },
        onError: (error) => {
          if (applyApiFieldErrors(form, error)) return;
          toast.error(error instanceof ApiError ? error.message : "Couldn't save changes, try again.");
        },
      },
    );
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <fieldset disabled={updateDocument.isPending} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="edit-title">Title</Label>
          <Input id="edit-title" {...form.register("title")} />
          {form.formState.errors.title && (
            <p className="text-destructive text-xs">{form.formState.errors.title.message}</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label>Category</Label>
            <Controller
              control={form.control}
              name="categoryId"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select category">
                      {(value: string) => categoryLabels[value] ?? "Select category"}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {categories?.map((category) => (
                      <SelectItem key={category.id} value={category.id}>
                        {category.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {form.formState.errors.categoryId && (
              <p className="text-destructive text-xs">{form.formState.errors.categoryId.message}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-review-date">Review due date</Label>
            <Input id="edit-review-date" type="date" {...form.register("reviewDueDate")} />
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="edit-description">Description</Label>
          <Textarea id="edit-description" rows={3} {...form.register("description")} />
        </div>

        <div className="space-y-1.5">
          <Label>Tags</Label>
          <TagInput value={tags} onChange={setTags} />
        </div>
      </fieldset>

      <div className="flex justify-end gap-2 pt-1">
        <Button type="button" variant="outline" onClick={onDone} disabled={updateDocument.isPending}>
          Cancel
        </Button>
        <Button type="submit" disabled={updateDocument.isPending}>
          {updateDocument.isPending ? "Saving…" : "Save"}
        </Button>
      </div>
    </form>
  );
}
