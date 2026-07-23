"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useMergeTag, useTags } from "@/features/taxonomy/hooks";
import { ApiError } from "@/lib/api-client";
import type { Tag } from "@/features/taxonomy/types";

interface MergeTagDialogProps {
  tag: Tag | null;
  onOpenChange: (open: boolean) => void;
}

export function MergeTagDialog({ tag, onOpenChange }: MergeTagDialogProps) {
  const { data: allTags } = useTags();
  const mergeTag = useMergeTag(tag?.id ?? "");
  const [targetId, setTargetId] = useState("");

  const candidates = (allTags ?? []).filter((t) => t.id !== tag?.id);
  const targetLabels: Record<string, string> = {};
  candidates.forEach((t) => (targetLabels[t.id] = t.name));

  function handleOpenChange(next: boolean) {
    if (mergeTag.isPending) return;
    if (!next) setTargetId("");
    onOpenChange(next);
  }

  function handleConfirm() {
    if (!targetId || !tag) return;
    const targetName = targetLabels[targetId];
    mergeTag.mutate(targetId, {
      onSuccess: (result) => {
        toast.success(`Merged "${tag.name}" into "${targetName}" — ${result.documentsUpdated} document(s) updated`);
        setTargetId("");
        onOpenChange(false);
      },
      onError: (error) => {
        toast.error(error instanceof ApiError ? error.message : "Couldn't merge this tag, try again.");
      },
    });
  }

  return (
    <Dialog open={Boolean(tag)} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Merge &ldquo;{tag?.name}&rdquo; into…</DialogTitle>
          <DialogDescription>
            {tag && tag.usageCount > 0
              ? `Used by ${tag.usageCount} document(s) — they'll be re-tagged with the target tag instead, and "${tag.name}" will be deleted.`
              : `"${tag?.name}" isn't used by any documents yet — merging just deletes it in favor of the target tag.`}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1.5">
          <Label>Target tag</Label>
          <Select value={targetId} onValueChange={(value) => setTargetId(value ?? "")} disabled={mergeTag.isPending}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select a tag">{(value: string) => targetLabels[value] ?? "Select a tag"}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              {candidates.map((candidate) => (
                <SelectItem key={candidate.id} value={candidate.id}>
                  {candidate.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={mergeTag.isPending}>
            Cancel
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={mergeTag.isPending || !targetId}>
            {mergeTag.isPending ? "Merging…" : "Merge"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
