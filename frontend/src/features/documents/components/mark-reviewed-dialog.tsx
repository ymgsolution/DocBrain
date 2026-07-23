"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useMarkReviewed } from "@/features/documents/hooks";
import { ApiError } from "@/lib/api-client";

interface MarkReviewedDialogProps {
  documentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function MarkReviewedDialog({ documentId, open, onOpenChange }: MarkReviewedDialogProps) {
  const [note, setNote] = useState("");
  const markReviewed = useMarkReviewed(documentId);

  function handleConfirm() {
    markReviewed.mutate(note || undefined, {
      onSuccess: (document) => {
        const nextDue = document.reviewDueDate;
        toast.success(nextDue ? `Marked reviewed — next review due ${nextDue}` : "Marked reviewed");
        setNote("");
        onOpenChange(false);
      },
      onError: (error) => {
        toast.error(error instanceof ApiError ? error.message : "Couldn't mark as reviewed, try again.");
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !markReviewed.isPending && onOpenChange(next)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Mark as reviewed</DialogTitle>
          <DialogDescription>Resets the review due date based on this category&rsquo;s review period.</DialogDescription>
        </DialogHeader>
        <div className="space-y-1.5">
          <Label htmlFor="review-note">Note (optional)</Label>
          <Textarea
            id="review-note"
            placeholder="Confirmed still accurate, no changes needed"
            rows={3}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            disabled={markReviewed.isPending}
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={markReviewed.isPending}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={markReviewed.isPending}>
            {markReviewed.isPending ? "Saving…" : "Mark as reviewed"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
