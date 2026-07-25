"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Sparkles, Check, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { useUpdateDocument, useReviewAiSuggestion } from "@/features/documents/hooks";
import type { DocumentDetail } from "@/types/document";

// AI feature track (Phase 2) — shadow-mode suggestions, shown read-only /
// accept-or-skip only. Accept actions reuse the existing update-document
// mutation (same one Edit Metadata uses) rather than any new endpoint.
export function AiSuggestionsCard({ document }: { document: DocumentDetail }) {
  const suggestion = document.aiSuggestion;
  const update = useUpdateDocument(document.id);
  const review = useReviewAiSuggestion(document.id);

  // suggestion.accepted is persisted server-side (POST .../ai-suggestion/review)
  // once a user finishes handling this suggestion — starting local state from
  // it means an already-reviewed suggestion doesn't re-offer itself after a
  // refresh, unlike plain useState(false) which forgets on every page load.
  const [titleHandled, setTitleHandled] = useState(suggestion?.accepted ?? false);
  const [tagsHandled, setTagsHandled] = useState(suggestion?.accepted ?? false);

  if (!suggestion || (!suggestion.title && !suggestion.summary && suggestion.tags.length === 0)) {
    return null;
  }

  const hasTitlePart = Boolean(suggestion.title);
  const hasTagsPart = suggestion.tags.length > 0;
  const showTitle = hasTitlePart && !titleHandled;
  const showTags = hasTagsPart && !tagsHandled;

  // Once every actionable part has a decision, tell the backend so it stays
  // remembered — checked against the *next* values being applied, not the
  // (stale, pre-update) titleHandled/tagsHandled closed over by the caller.
  function markReviewedIfDone(nextTitleHandled: boolean, nextTagsHandled: boolean) {
    const titleDone = !hasTitlePart || nextTitleHandled;
    const tagsDone = !hasTagsPart || nextTagsHandled;
    if (titleDone && tagsDone && !suggestion?.accepted) {
      review.mutate();
    }
  }

  function acceptTitle() {
    if (!suggestion?.title) return;
    update.mutate(
      { title: suggestion.title },
      {
        onSuccess: () => {
          setTitleHandled(true);
          toast.success("Title updated");
          markReviewedIfDone(true, tagsHandled);
        },
        onError: (err) => toast.error(err instanceof ApiError ? err.message : "Couldn't update the title."),
      },
    );
  }

  function keepTitle() {
    setTitleHandled(true);
    markReviewedIfDone(true, tagsHandled);
  }

  function acceptTags() {
    if (!suggestion) return;
    const existing = document.tags.map((t) => t.name);
    const existingLower = new Set(existing.map((n) => n.toLowerCase()));
    const merged = [...existing, ...suggestion.tags.filter((t) => !existingLower.has(t.toLowerCase()))];
    update.mutate(
      { tags: merged },
      {
        onSuccess: () => {
          setTagsHandled(true);
          toast.success("Tags updated");
          markReviewedIfDone(titleHandled, true);
        },
        onError: (err) => toast.error(err instanceof ApiError ? err.message : "Couldn't update tags."),
      },
    );
  }

  function skipTags() {
    setTagsHandled(true);
    markReviewedIfDone(titleHandled, true);
  }

  // Nothing left to act on and no summary to show — no point in a card with
  // just a floating "AI Suggestions" header over an empty body.
  if (!showTitle && !showTags && !suggestion.summary) return null;

  return (
    <div className="border-border bg-muted/30 space-y-4 rounded-xl border p-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Sparkles className="text-primary size-4" />
        AI Suggestions
      </div>

      {showTitle && (
        <div className="space-y-2">
          <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">Suggested Title</p>
          <p className="text-sm">{suggestion.title}</p>
          <div className="flex gap-2">
            <Button size="sm" onClick={acceptTitle} disabled={update.isPending}>
              <Check className="size-3.5" /> Accept Title
            </Button>
            <Button size="sm" variant="outline" onClick={keepTitle}>
              <X className="size-3.5" /> Keep Current
            </Button>
          </div>
        </div>
      )}

      {showTags && (
        <div className="space-y-2">
          <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">Suggested Tags</p>
          <div className="flex flex-wrap gap-1.5">
            {suggestion.tags.map((tag) => (
              <Badge key={tag} variant="secondary">
                {tag}
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <Button size="sm" onClick={acceptTags} disabled={update.isPending}>
              <Check className="size-3.5" /> Accept Tags
            </Button>
            <Button size="sm" variant="outline" onClick={skipTags}>
              <X className="size-3.5" /> Skip
            </Button>
          </div>
        </div>
      )}

      {suggestion.summary && (
        <div className="space-y-1">
          <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">AI Summary</p>
          <p className="text-muted-foreground text-sm">{suggestion.summary}</p>
        </div>
      )}
    </div>
  );
}
