"use client";

import { useState } from "react";
import { toast } from "sonner";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { UploadDropzone } from "@/components/shared/upload-dropzone";
import { FileTypeIcon } from "@/components/shared/file-type-icon";
import { useUploadVersion } from "@/features/documents/hooks";
import { validateUploadFile } from "@/lib/upload-constants";
import { formatFileSize } from "@/lib/format";
import { ApiError } from "@/lib/api-client";

const MIN_NOTE_LENGTH = 5;

interface UploadVersionDialogProps {
  documentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function UploadVersionDialog({ documentId, open, onOpenChange }: UploadVersionDialogProps) {
  const uploadVersion = useUploadVersion(documentId);

  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [changeNote, setChangeNote] = useState("");

  function resetForm() {
    setFile(null);
    setFileError(null);
    setChangeNote("");
  }

  function handleOpenChange(next: boolean) {
    if (uploadVersion.isPending) return; // modal cannot be dismissed mid-upload
    if (!next) resetForm();
    onOpenChange(next);
  }

  function handleFileSelected(selected: File) {
    const error = validateUploadFile(selected);
    if (error) {
      setFileError(error);
      setFile(null);
      return;
    }
    setFileError(null);
    setFile(selected);
  }

  function handleSubmit() {
    if (!file) {
      setFileError("Select a file to upload.");
      return;
    }
    if (changeNote.trim().length < MIN_NOTE_LENGTH) return;

    uploadVersion.mutate(
      { file, changeNote: changeNote.trim() },
      {
        onSuccess: (version) => {
          toast.success(`Version ${version.versionNumber} uploaded`);
          resetForm();
          onOpenChange(false);
        },
        onError: (error) => {
          toast.error(error instanceof ApiError ? error.message : "Upload failed — nothing was saved, retry?");
        },
      },
    );
  }

  const noteTooShort = changeNote.length > 0 && changeNote.trim().length < MIN_NOTE_LENGTH;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg" showCloseButton={!uploadVersion.isPending}>
        <DialogHeader>
          <DialogTitle>Upload new version</DialogTitle>
          <DialogDescription>The new file becomes the current version; earlier versions stay in history.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
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
              {!uploadVersion.isPending && (
                <Button type="button" variant="ghost" size="icon-sm" aria-label="Remove file" onClick={() => setFile(null)}>
                  <X className="size-4" />
                </Button>
              )}
            </div>
          )}

          {uploadVersion.isPending && (
            <div className="space-y-1.5">
              <Progress value={uploadVersion.progress} />
              <p className="text-muted-foreground text-xs tabular-nums">{uploadVersion.progress}%</p>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="version-change-note">Change note</Label>
            <Textarea
              id="version-change-note"
              placeholder="What changed in this version?"
              rows={2}
              value={changeNote}
              onChange={(e) => setChangeNote(e.target.value)}
              disabled={uploadVersion.isPending}
            />
            {noteTooShort && (
              <p className="text-destructive text-xs">Change note must be at least {MIN_NOTE_LENGTH} characters.</p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={uploadVersion.isPending}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={uploadVersion.isPending || !file || changeNote.trim().length < MIN_NOTE_LENGTH}
          >
            {uploadVersion.isPending ? "Uploading…" : "Upload version"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
