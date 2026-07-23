"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useRenameTag } from "@/features/taxonomy/hooks";
import { ApiError } from "@/lib/api-client";
import type { Tag } from "@/features/taxonomy/types";

const renameSchema = z.object({
  name: z.string().min(1, "Name is required").max(50),
});

type RenameValues = z.infer<typeof renameSchema>;

interface RenameTagDialogProps {
  tag: Tag | null;
  onOpenChange: (open: boolean) => void;
}

export function RenameTagDialog({ tag, onOpenChange }: RenameTagDialogProps) {
  const renameTag = useRenameTag(tag?.id ?? "");

  const form = useForm<RenameValues>({
    resolver: zodResolver(renameSchema),
    values: { name: tag?.name ?? "" },
  });

  function handleOpenChange(next: boolean) {
    if (renameTag.isPending) return;
    if (!next) form.reset();
    onOpenChange(next);
  }

  function onSubmit(values: RenameValues) {
    renameTag.mutate(values.name, {
      onSuccess: () => {
        toast.success("Tag renamed");
        form.reset();
        onOpenChange(false);
      },
      onError: (error) => {
        toast.error(error instanceof ApiError ? error.message : "Couldn't rename this tag, try again.");
      },
    });
  }

  return (
    <Dialog open={Boolean(tag)} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Rename tag</DialogTitle>
          <DialogDescription>Applies everywhere this tag is used.</DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="space-y-1.5">
            <Label htmlFor="tag-name">Name</Label>
            <Input id="tag-name" disabled={renameTag.isPending} {...form.register("name")} />
            {form.formState.errors.name && (
              <p className="text-destructive text-xs">{form.formState.errors.name.message}</p>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={renameTag.isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={renameTag.isPending}>
              {renameTag.isPending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
