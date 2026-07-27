"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Check, Copy, Link2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
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
import { ApiError } from "@/lib/api-client";
import { useCreateShareLink, useRevokeShareLink, useShareLinks } from "@/features/shares/hooks";
import type { ShareLinkCreated } from "@/types/share";

const EXPIRY_OPTIONS = [
  { value: "1", label: "1 day" },
  { value: "7", label: "7 days" },
  { value: "30", label: "30 days" },
  { value: "90", label: "90 days" },
];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

interface ShareDialogProps {
  documentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ShareDialog({ documentId, open, onOpenChange }: ShareDialogProps) {
  const [expiresInDays, setExpiresInDays] = useState("7");
  // Held in component state, not refetched: the raw token exists only in the
  // create response, so once this dialog closes the URL genuinely cannot be
  // shown again — the owner has to revoke and issue a new one.
  const [justCreated, setJustCreated] = useState<ShareLinkCreated | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: links, isLoading } = useShareLinks(documentId, open);
  const createLink = useCreateShareLink(documentId);
  const revokeLink = useRevokeShareLink(documentId);

  function handleCreate() {
    createLink.mutate(Number(expiresInDays), {
      onSuccess: (link) => {
        setJustCreated(link);
        setCopied(false);
        toast.success("Share link created");
      },
      onError: (error) =>
        toast.error(error instanceof ApiError ? error.message : "Couldn't create a share link, try again."),
    });
  }

  async function handleCopy() {
    if (!justCreated) return;
    try {
      await navigator.clipboard.writeText(justCreated.url);
      setCopied(true);
      toast.success("Link copied");
    } catch {
      // Clipboard access can be denied (permissions, insecure context) —
      // the input stays selectable so copying by hand still works.
      toast.error("Couldn't copy automatically — select the link and copy it.");
    }
  }

  function handleRevoke(linkId: string) {
    revokeLink.mutate(linkId, {
      onSuccess: () => {
        if (justCreated?.id === linkId) setJustCreated(null);
        toast.success("Link revoked");
      },
      onError: (error) =>
        toast.error(error instanceof ApiError ? error.message : "Couldn't revoke that link, try again."),
    });
  }

  function handleOpenChange(next: boolean) {
    if (!next) setJustCreated(null);
    onOpenChange(next);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Share externally</DialogTitle>
          <DialogDescription>
            Anyone with the link can view this document without signing in. It&apos;s view-only, expires
            automatically, and always shows the version as it is right now.
          </DialogDescription>
        </DialogHeader>

        {justCreated ? (
          <div className="space-y-2">
            <Label htmlFor="share-url">Your link — copy it now, it won&apos;t be shown again</Label>
            <div className="flex gap-2">
              <Input id="share-url" readOnly value={justCreated.url} onFocus={(e) => e.target.select()} />
              <Button type="button" variant="outline" onClick={handleCopy} aria-label="Copy link">
                {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
              </Button>
            </div>
            <p className="text-muted-foreground text-xs">Expires {formatDate(justCreated.expiresAt)}</p>
          </div>
        ) : (
          <div className="flex items-end gap-2">
            <div className="flex-1 space-y-2">
              <Label htmlFor="share-expiry">Expires after</Label>
              {/* Base UI's Select can emit null on clear; the expiry is
                  never optional here, so a null is simply ignored. */}
              <Select value={expiresInDays} onValueChange={(value) => value && setExpiresInDays(value)}>
                <SelectTrigger id="share-expiry" className="w-full">
                  <SelectValue>{EXPIRY_OPTIONS.find((o) => o.value === expiresInDays)?.label}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {EXPIRY_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="button" onClick={handleCreate} disabled={createLink.isPending}>
              {createLink.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Link2 className="size-4" />
              )}
              Create link
            </Button>
          </div>
        )}

        <div className="space-y-2">
          <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">Existing links</p>
          {isLoading ? (
            <p className="text-muted-foreground text-sm">Loading…</p>
          ) : !links?.length ? (
            <p className="text-muted-foreground text-sm">No links yet.</p>
          ) : (
            <ul className="divide-border divide-y">
              {links.map((link) => (
                <li key={link.id} className="flex items-center justify-between gap-3 py-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm">v{link.versionNumber}</span>
                      {link.isActive ? (
                        <Badge variant="outline">Active</Badge>
                      ) : (
                        <Badge variant="secondary">{link.revokedAt ? "Revoked" : "Expired"}</Badge>
                      )}
                    </div>
                    <p className="text-muted-foreground truncate text-xs">
                      Expires {formatDate(link.expiresAt)} · {link.viewCount}{" "}
                      {link.viewCount === 1 ? "view" : "views"}
                    </p>
                  </div>
                  {link.isActive && (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => handleRevoke(link.id)}
                      disabled={revokeLink.isPending}
                    >
                      Revoke
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
