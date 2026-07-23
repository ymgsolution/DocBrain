import { FileTypeIcon } from "@/components/shared/file-type-icon";
import { DownloadLink } from "@/components/shared/download-link";
import { getVersionContentUrl } from "@/lib/api-client";
import { formatFileSize } from "@/lib/format";
import type { VersionSummary } from "@/types/document";

// Mirrors the backend's own inline-eligibility rule (versions/router.py's
// _resolve_disposition) so we only attempt an inline preview for types the
// server will actually serve with Content-Disposition: inline — otherwise
// the browser would try to download inside the iframe instead of render.
const INLINE_PREVIEWABLE_MIME_TYPES = new Set(["application/pdf", "text/plain"]);

function isPreviewable(mimeType: string): boolean {
  return INLINE_PREVIEWABLE_MIME_TYPES.has(mimeType) || mimeType.startsWith("image/");
}

export function DocumentPreview({ documentId, version }: { documentId: string; version: VersionSummary | null }) {
  if (!version) return null;

  const inlineUrl = getVersionContentUrl(documentId, version.versionNumber, "inline");

  if (!isPreviewable(version.mimeType)) {
    return (
      <div className="border-border flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed py-16">
        <div className="bg-muted text-muted-foreground flex size-12 items-center justify-center rounded-full">
          <FileTypeIcon filename={version.originalFilename} className="size-6" />
        </div>
        <div className="text-center">
          <p className="text-sm font-medium">{version.originalFilename}</p>
          <p className="text-muted-foreground text-xs">{formatFileSize(version.sizeBytes)} · Preview not available</p>
        </div>
        <DownloadLink documentId={documentId} versionNumber={version.versionNumber} filename={version.originalFilename} />
      </div>
    );
  }

  if (version.mimeType.startsWith("image/")) {
    return (
      <div className="bg-muted/30 flex items-center justify-center rounded-xl border p-4">
        {/* eslint-disable-next-line @next/next/no-img-element -- authenticated same-origin BFF URL, not an optimizable remote image */}
        <img src={inlineUrl} alt={version.originalFilename} className="max-h-[600px] w-full rounded-lg object-contain" />
      </div>
    );
  }

  return (
    <iframe
      src={inlineUrl}
      title={version.originalFilename}
      className="h-[600px] w-full rounded-xl border"
    />
  );
}
