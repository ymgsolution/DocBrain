import type { Metadata } from "next";
import { FileText, Clock, ShieldOff } from "lucide-react";
import { API_BASE_URL } from "@/lib/constants";
import { formatFileSize } from "@/lib/format";
import type { PublicSharedDocument } from "@/types/share";

// Lives outside the (app) route group on purpose, so it renders with the
// root layout only — no sidebar, no topbar, no session, nothing that hints
// at the internal workspace. See proxy.ts for why /share/ is matched
// separately from the login-only public paths.

export const metadata: Metadata = {
  title: "Shared document · DocBrain",
  // A shared document must never end up in a search index. The API sends
  // X-Robots-Tag as well; this covers the HTML page itself.
  robots: { index: false, follow: false },
};

const INLINE_PREVIEWABLE = new Set(["application/pdf", "text/plain"]);

function isPreviewable(mimeType: string): boolean {
  return INLINE_PREVIEWABLE.has(mimeType) || mimeType.startsWith("image/");
}

// Fetched server-side, straight from the API. Deliberately not the browser's
// job: it keeps the token out of any client-side request log, and means an
// invalid link renders as a page rather than flashing a broken layout first.
async function fetchShared(token: string): Promise<PublicSharedDocument | null> {
  const response = await fetch(`${API_BASE_URL}/api/v1/public/shares/${encodeURIComponent(token)}`, {
    cache: "no-store",
  });
  if (!response.ok) return null;
  return response.json();
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-4xl flex-col gap-6 px-4 py-10 sm:px-6">
      <header className="flex items-center gap-2 text-sm font-medium">
        <FileText className="text-primary size-5" />
        DocBrain
      </header>
      {children}
    </main>
  );
}

export default async function SharedDocumentPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const shared = await fetchShared(token);

  // One message for every failure — unknown, expired, revoked, or a deleted
  // document — matching the API, which deliberately doesn't distinguish
  // them either. Telling a stranger *which* it was is free information.
  if (!shared) {
    return (
      <Shell>
        <div className="border-border flex flex-col items-center gap-3 rounded-xl border border-dashed py-16 text-center">
          <div className="bg-muted text-muted-foreground flex size-12 items-center justify-center rounded-full">
            <ShieldOff className="size-6" />
          </div>
          <div>
            <p className="text-sm font-medium">This link isn&apos;t available</p>
            <p className="text-muted-foreground mt-1 text-sm">
              It may have expired, been revoked, or never existed. Ask whoever shared it for a new link.
            </p>
          </div>
        </div>
      </Shell>
    );
  }

  const contentUrl = `/api/public/shares/${encodeURIComponent(token)}/content`;
  const expires = new Date(shared.expiresAt);

  return (
    <Shell>
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight break-words">{shared.title}</h1>
        <p className="text-muted-foreground text-sm">
          {shared.originalFilename} · {formatFileSize(shared.sizeBytes)} · v{shared.versionNumber}
        </p>
      </div>

      <div className="text-muted-foreground border-border bg-muted/30 flex items-center gap-2 rounded-lg border px-3 py-2 text-xs">
        <Clock className="size-3.5 shrink-0" />
        <span>
          Shared with you, view-only. This link expires on{" "}
          {expires.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}.
        </span>
      </div>

      {isPreviewable(shared.mimeType) ? (
        shared.mimeType.startsWith("image/") ? (
          // eslint-disable-next-line @next/next/no-img-element -- same-origin proxied stream, not an optimizable remote image
          <img src={contentUrl} alt={shared.originalFilename} className="w-full rounded-xl border object-contain" />
        ) : (
          <iframe src={contentUrl} title={shared.originalFilename} className="h-[70vh] w-full rounded-xl border" />
        )
      ) : (
        <div className="border-border flex flex-col items-center gap-3 rounded-xl border border-dashed py-16 text-center">
          <div className="bg-muted text-muted-foreground flex size-12 items-center justify-center rounded-full">
            <FileText className="size-6" />
          </div>
          <div>
            <p className="text-sm font-medium">Preview isn&apos;t available for this file type</p>
            <p className="text-muted-foreground mt-1 text-sm">
              This document was shared as view-only, so it can&apos;t be downloaded.
            </p>
          </div>
        </div>
      )}
    </Shell>
  );
}
