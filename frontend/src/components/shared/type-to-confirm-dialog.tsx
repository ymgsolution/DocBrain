"use client";

import { useState } from "react";
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

interface TypeToConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmText: string;
  confirmLabel?: string;
  loading?: boolean;
  onConfirm: () => void;
}

// For the rare, truly irreversible actions (permanent delete) where the
// standard destructive ConfirmDialog isn't enough friction — the user must
// type the exact target name, not just click a button.
export function TypeToConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText,
  confirmLabel = "Delete permanently",
  loading = false,
  onConfirm,
}: TypeToConfirmDialogProps) {
  const [value, setValue] = useState("");

  function handleOpenChange(next: boolean) {
    if (loading) return;
    if (!next) setValue("");
    onOpenChange(next);
  }

  const matches = value === confirmText;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="space-y-1.5">
          <Label htmlFor="type-to-confirm-input">
            Type <span className="font-mono font-medium">{confirmText}</span> to confirm
          </Label>
          <Input
            id="type-to-confirm-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={loading}
            autoComplete="off"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button variant="destructive" disabled={!matches || loading} onClick={onConfirm}>
            {loading ? "Deleting…" : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
