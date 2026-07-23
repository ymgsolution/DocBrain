"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, Controller } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { UploadDropzone } from "@/components/shared/upload-dropzone";
import { FileTypeIcon } from "@/components/shared/file-type-icon";
import { TagInput } from "./tag-input";
import { useCategories } from "@/features/taxonomy/hooks";
import { useCreateDocument } from "@/features/documents/hooks";
import { validateUploadFile } from "@/lib/upload-constants";
import { formatFileSize } from "@/lib/format";
import { ApiError } from "@/lib/api-client";
import { applyApiFieldErrors } from "@/lib/form-errors";

const uploadSchema = z.object({
  title: z.string().min(3, "Title must be at least 3 characters").max(200),
  categoryId: z.string().min(1, "Category is required"),
  description: z.string().max(1000).optional().or(z.literal("")),
  reviewDueDate: z.string().optional().or(z.literal("")),
});

type UploadValues = z.infer<typeof uploadSchema>;

interface UploadDocumentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function UploadDocumentDialog({ open, onOpenChange }: UploadDocumentDialogProps) {
  const router = useRouter();
  const { data: categories } = useCategories();
  const createDocument = useCreateDocument();

  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [tags, setTags] = useState<string[]>([]);

  const form = useForm<UploadValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: { title: "", categoryId: "", description: "", reviewDueDate: "" },
  });

  const categoryLabels: Record<string, string> = {};
  categories?.forEach((c) => (categoryLabels[c.id] = c.name));

  function handleFileSelected(selected: File) {
    const error = validateUploadFile(selected);
    if (error) {
      setFileError(error);
      setFile(null);
      return;
    }
    setFileError(null);
    setFile(selected);
    if (!form.getValues("title")) {
      form.setValue("title", selected.name.replace(/\.[^.]+$/, ""));
    }
  }

  function resetForm() {
    form.reset();
    setFile(null);
    setFileError(null);
    setTags([]);
  }

  function handleOpenChange(next: boolean) {
    if (createDocument.isPending) return; // modal cannot be dismissed mid-upload
    if (!next) resetForm();
    onOpenChange(next);
  }

  function onSubmit(values: UploadValues) {
    if (!file) {
      setFileError("Select a file to upload.");
      return;
    }
    createDocument.mutate(
      {
        file,
        title: values.title,
        categoryId: values.categoryId,
        description: values.description || undefined,
        tags,
        reviewDueDate: values.reviewDueDate || undefined,
      },
      {
        onSuccess: (document) => {
          toast.success(`"${document.title}" uploaded (v1)`, {
            action: { label: "View document", onClick: () => router.push(`/documents/${document.id}`) },
          });
          resetForm();
          onOpenChange(false);
        },
        onError: (error) => {
          if (applyApiFieldErrors(form, error)) return;
          toast.error(error instanceof ApiError ? error.message : "Upload failed — nothing was saved, retry?");
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg" showCloseButton={!createDocument.isPending}>
        <DialogHeader>
          <DialogTitle>Upload document</DialogTitle>
          <DialogDescription>Add a new document to your organization&rsquo;s library.</DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {!file ? (
            <div className="space-y-1.5">
              <UploadDropzone onFileSelected={handleFileSelected} />
              {fileError && <p className="text-destructive text-xs">{fileError}</p>}
            </div>
          ) : (
            <div className="border-border flex items-center gap-3 rounded-lg border p-3">
              <div className="bg-muted text-muted-foreground flex size-9 shrink-0 items-center justify-center rounded-md">
                <FileTypeIcon filename={file.name} className="size-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{file.name}</p>
                <p className="text-muted-foreground text-xs">{formatFileSize(file.size)}</p>
              </div>
              {!createDocument.isPending && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Remove file"
                  onClick={() => setFile(null)}
                >
                  <X className="size-4" />
                </Button>
              )}
            </div>
          )}

          {createDocument.isPending && (
            <div className="space-y-1.5">
              <Progress value={createDocument.progress} />
              <p className="text-muted-foreground text-xs tabular-nums">{createDocument.progress}%</p>
            </div>
          )}

          <fieldset disabled={createDocument.isPending} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="upload-title">Title</Label>
              <Input id="upload-title" placeholder="Document title" {...form.register("title")} />
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
                <Label htmlFor="upload-review-date">Review due date</Label>
                <Input id="upload-review-date" type="date" {...form.register("reviewDueDate")} />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="upload-description">Description</Label>
              <Textarea id="upload-description" placeholder="Optional" rows={2} {...form.register("description")} />
            </div>

            <div className="space-y-1.5">
              <Label>Tags</Label>
              <TagInput value={tags} onChange={setTags} />
            </div>
          </fieldset>
        </form>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={createDocument.isPending}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={form.handleSubmit(onSubmit)}
            disabled={createDocument.isPending || !file}
          >
            {createDocument.isPending ? "Uploading…" : "Upload document"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
