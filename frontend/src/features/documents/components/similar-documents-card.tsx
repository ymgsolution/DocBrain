"use client";

import Link from "next/link";
import { Layers } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/error-state";
import { FileTypeIcon } from "@/components/shared/file-type-icon";
import { ApiError } from "@/lib/api-client";
import { formatSimilarityScore } from "@/lib/format";
import { useSimilarDocuments } from "@/features/documents/hooks";

const CARD_HEADER = (
  <div className="flex items-center gap-2 text-sm font-medium">
    <Layers className="text-primary size-4" />
    Similar Documents
  </div>
);

// Similar Document Detection track — unlike AiSuggestionsCard, this data
// isn't embedded in DocumentDetail (it's an active nearest-neighbor query
// against every other document's embedding), so it needs its own query and
// its own loading/error states rather than just reading a field.
export function SimilarDocumentsCard({ documentId }: { documentId: string }) {
  const { data: similarDocuments, isLoading, isError, error, refetch } = useSimilarDocuments(documentId);

  if (isError) {
    return (
      <div className="border-border bg-muted/30 space-y-4 rounded-xl border p-4">
        {CARD_HEADER}
        <ErrorState
          message={error instanceof ApiError ? error.message : "Couldn't load similar documents."}
          correlationId={error instanceof ApiError ? error.correlationId : undefined}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  if (isLoading || !similarDocuments) {
    return (
      <div className="border-border bg-muted/30 space-y-4 rounded-xl border p-4">
        {CARD_HEADER}
        <div className="space-y-2">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  // Nothing to show — either this document's embedding isn't ready yet, or
  // there genuinely are no similar documents. Same "quiet, self-clearing"
  // convention as AiSuggestionsCard: no clutter on every document.
  if (similarDocuments.length === 0) {
    return null;
  }

  return (
    <div className="border-border bg-muted/30 space-y-4 rounded-xl border p-4">
      {CARD_HEADER}
      <div className="space-y-1.5">
        {similarDocuments.map((document) => (
          <Link
            key={document.id}
            href={`/documents/${document.id}`}
            className="hover:bg-background flex items-center gap-3 rounded-lg p-2 transition-colors"
          >
            <div className="bg-muted text-muted-foreground flex size-8 shrink-0 items-center justify-center rounded-md">
              <FileTypeIcon filename={document.currentVersion?.originalFilename ?? document.title} className="size-4" />
            </div>
            <p className="min-w-0 flex-1 truncate text-sm font-medium">{document.title}</p>
            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 shrink-0 font-normal">
              {formatSimilarityScore(document.similarity)}
            </Badge>
          </Link>
        ))}
      </div>
    </div>
  );
}
