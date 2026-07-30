"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useUpdateOrganizationSettings } from "@/features/platform/hooks";
import { ApiError } from "@/lib/api-client";
import { formatFileSize } from "@/lib/format";
import type { OrganizationStats } from "@/features/platform/types";

const MB = 1024 * 1024;

interface OrganizationSettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  organization: OrganizationStats;
}

export function OrganizationSettingsDialog({
  open,
  onOpenChange,
  organization,
}: OrganizationSettingsDialogProps) {
  const { settings, storage } = organization;
  const update = useUpdateOrganizationSettings(organization.id);

  const [aiSuggestions, setAiSuggestions] = useState(settings.aiSuggestionsEnabled);
  const [duplicateDetection, setDuplicateDetection] = useState(settings.duplicateDetectionEnabled);
  const [limitMb, setLimitMb] = useState(String(settings.storageLimitMb));

  const parsedLimit = Number(limitMb);
  const limitIsValid = Number.isInteger(parsedLimit) && parsedLimit >= 1 && parsedLimit <= 1_000_000;

  const limitBytes = settings.storageLimitMb * MB;
  const percentUsed = limitBytes > 0 ? Math.min(100, (storage.totalBytes / limitBytes) * 100) : 0;
  const isOverLimit = storage.totalBytes > limitBytes;
  // Everything that isn't a current version of an active document — the part
  // an admin can't see anywhere in the app but is still paying for.
  const hiddenBytes = storage.supersededBytes + storage.trashedBytes;

  function handleOpenChange(next: boolean) {
    if (update.isPending) return;
    if (!next) {
      // Reset to the server's values so a cancelled edit doesn't persist in
      // local state the next time this dialog opens.
      setAiSuggestions(settings.aiSuggestionsEnabled);
      setDuplicateDetection(settings.duplicateDetectionEnabled);
      setLimitMb(String(settings.storageLimitMb));
    }
    onOpenChange(next);
  }

  function handleSave() {
    if (!limitIsValid) return;
    update.mutate(
      {
        aiSuggestionsEnabled: aiSuggestions,
        duplicateDetectionEnabled: duplicateDetection,
        storageLimitMb: parsedLimit,
      },
      {
        onSuccess: () => {
          toast.success(`Settings saved for ${organization.name}`);
          onOpenChange(false);
        },
        onError: (error) => {
          toast.error(error instanceof ApiError ? error.message : "Couldn't save these settings, try again.");
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Settings for {organization.name}</DialogTitle>
          <DialogDescription>
            These apply to everyone in {organization.name}. Only platform admins can change them.
          </DialogDescription>
        </DialogHeader>

        <fieldset disabled={update.isPending} className="space-y-5">
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <Checkbox
                id="ai-suggestions"
                checked={aiSuggestions}
                onCheckedChange={(checked) => setAiSuggestions(checked === true)}
              />
              <div className="space-y-0.5">
                <Label htmlFor="ai-suggestions">AI Suggestions</Label>
                <p className="text-muted-foreground text-xs">
                  Suggested titles, summaries and tags on newly uploaded documents.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Checkbox
                id="duplicate-detection"
                checked={duplicateDetection}
                onCheckedChange={(checked) => setDuplicateDetection(checked === true)}
              />
              <div className="space-y-0.5">
                <Label htmlFor="duplicate-detection">Duplicate Detection</Label>
                <p className="text-muted-foreground text-xs">
                  Similar Documents, powered by embeddings generated at upload time.
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="storage-limit">Storage limit (MB)</Label>
            <Input
              id="storage-limit"
              inputMode="numeric"
              value={limitMb}
              onChange={(event) => setLimitMb(event.target.value)}
            />
            {!limitIsValid && <p className="text-destructive text-xs">Enter a whole number between 1 and 1,000,000.</p>}
            <p className="text-muted-foreground text-xs">
              Total for the whole organization, not a per-file limit.
            </p>
          </div>

          {/* The breakdown, not just a total. The app only ever shows current
              versions of active documents, so an admin who adds up what they
              can see will land well under this figure — 38% under, for the
              largest organization here. Naming the difference is what stops
              the number reading as broken. */}
          <div className="border-border space-y-2 rounded-lg border p-3">
            <div className="flex items-baseline justify-between">
              <span className="text-sm font-medium">Storage used</span>
              <span className={`text-sm ${isOverLimit ? "text-destructive font-medium" : "text-muted-foreground"}`}>
                {formatFileSize(storage.totalBytes)} of {settings.storageLimitMb} MB
              </span>
            </div>
            <Progress value={percentUsed} />
            <dl className="text-muted-foreground space-y-1 text-xs">
              <div className="flex justify-between">
                <dt>Current documents</dt>
                <dd>{formatFileSize(storage.activeCurrentBytes)}</dd>
              </div>
              <div className="flex justify-between">
                <dt>Older versions</dt>
                <dd>{formatFileSize(storage.supersededBytes)}</dd>
              </div>
              <div className="flex justify-between">
                <dt>In Trash</dt>
                <dd>{formatFileSize(storage.trashedBytes)}</dd>
              </div>
            </dl>
            {hiddenBytes > 0 && (
              <p className="text-muted-foreground border-border border-t pt-2 text-xs">
                {/* Explicit {" "} rather than a literal space: the text node
                    below spans several lines, and JSX trims the leading
                    whitespace off its first line — which rendered "18 MBof
                    this" until this was added. */}
                {formatFileSize(hiddenBytes)}{" "}
                of this isn&apos;t visible in the document list. Older versions and trashed documents keep their
                files until a document is permanently deleted, which only an organization admin can do.
              </p>
            )}
            {isOverLimit && (
              <p className="text-destructive text-xs">
                This organization is over its limit. Nothing is deleted or hidden, but further uploads will be
                refused until space is freed or the limit is raised.
              </p>
            )}
          </div>
        </fieldset>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={update.isPending}>
            Cancel
          </Button>
          <Button type="button" onClick={handleSave} disabled={update.isPending || !limitIsValid}>
            {update.isPending ? "Saving…" : "Save settings"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
