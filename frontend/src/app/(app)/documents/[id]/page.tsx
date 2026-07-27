"use client";

import { useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { AppBreadcrumb } from "@/components/layout/app-breadcrumb";
import { ErrorState } from "@/components/shared/error-state";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { useCurrentUser } from "@/features/auth/hooks";
import { useDocument, useSoftDeleteDocument, useRestoreDocument } from "@/features/documents/hooks";
import { DocumentHeader } from "@/features/documents/components/document-header";
import { DocumentPreview } from "@/features/documents/components/document-preview";
import { MetadataPanel } from "@/features/documents/components/metadata-panel";
import { AiSuggestionsCard } from "@/features/documents/components/ai-suggestions-card";
import { SimilarDocumentsCard } from "@/features/documents/components/similar-documents-card";
import { EditMetadataForm } from "@/features/documents/components/edit-metadata-form";
import { MarkReviewedDialog } from "@/features/documents/components/mark-reviewed-dialog";
import { ShareDialog } from "@/features/documents/components/share-dialog";
import { VersionsTab } from "@/features/documents/components/versions-tab";
import { DocumentActivityTab } from "@/features/documents/components/activity-tab";

const UploadVersionDialog = dynamic(
  () => import("@/features/documents/components/upload-version-dialog").then((m) => m.UploadVersionDialog),
  { ssr: false },
);

export default function DocumentDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: user } = useCurrentUser();
  const { data: document, isLoading, isError, error, refetch } = useDocument(id);
  const softDelete = useSoftDeleteDocument(id);
  const restore = useRestoreDocument(id);

  const [editing, setEditing] = useState(false);
  const [markReviewedOpen, setMarkReviewedOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [uploadVersionOpen, setUploadVersionOpen] = useState(false);

  function handleDelete() {
    softDelete.mutate(undefined, {
      onSuccess: () => {
        setDeleteOpen(false);
        toast.success("Moved to Trash", {
          action: {
            label: "Undo",
            onClick: () => restore.mutate(),
          },
        });
        router.push("/documents");
      },
      onError: (err) => {
        toast.error(err instanceof ApiError ? err.message : "Couldn't delete this document, try again.");
      },
    });
  }

  if (isError) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <div className="space-y-6">
        <AppBreadcrumb segments={[{ label: "Documents", href: "/documents" }, { label: "Not found" }]} />
        <ErrorState
          title={notFound ? "Document not found" : "Something went wrong"}
          message={error instanceof ApiError ? error.message : undefined}
          correlationId={error instanceof ApiError ? error.correlationId : undefined}
          onRetry={notFound ? undefined : () => refetch()}
        />
        <div className="flex justify-center">
          <Button variant="outline" nativeButton={false} render={<Link href="/documents" />}>
            Back to Documents
          </Button>
        </div>
      </div>
    );
  }

  if (isLoading || !document || !user) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-10 w-2/3" />
        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <Skeleton className="h-96 rounded-xl" />
          <Skeleton className="h-96 rounded-xl" />
        </div>
      </div>
    );
  }

  const canManageVersions = document.owner.id === user.id || user.role === "REVIEWER" || user.role === "ADMIN";

  return (
    <div className="space-y-6">
      <AppBreadcrumb segments={[{ label: "Documents", href: "/documents" }, { label: document.title }]} />

      <DocumentHeader
        document={document}
        currentUser={user}
        editing={editing}
        onEdit={() => setEditing(true)}
        onDelete={() => setDeleteOpen(true)}
        onMarkReviewed={() => setMarkReviewedOpen(true)}
        onShare={() => setShareOpen(true)}
        onUploadVersion={() => setUploadVersionOpen(true)}
      />

      <AiSuggestionsCard document={document} />

      <SimilarDocumentsCard documentId={document.id} />

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="versions">Versions</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
            <DocumentPreview documentId={document.id} version={document.currentVersion} />
            <div className="border-border rounded-xl border p-4">
              {editing ? (
                <EditMetadataForm document={document} onDone={() => setEditing(false)} />
              ) : (
                <MetadataPanel document={document} />
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="versions" className="mt-4">
          <VersionsTab documentId={document.id} canManageVersions={canManageVersions} />
        </TabsContent>

        <TabsContent value="activity" className="mt-4">
          <DocumentActivityTab documentId={document.id} />
        </TabsContent>
      </Tabs>

      <MarkReviewedDialog documentId={document.id} open={markReviewedOpen} onOpenChange={setMarkReviewedOpen} />
      <ShareDialog documentId={document.id} open={shareOpen} onOpenChange={setShareOpen} />

      {uploadVersionOpen && (
        <UploadVersionDialog documentId={document.id} open={uploadVersionOpen} onOpenChange={setUploadVersionOpen} />
      )}

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Move to Trash?"
        description={`“${document.title}” will be moved to Trash. You can restore it later.`}
        confirmLabel="Move to Trash"
        destructive
        loading={softDelete.isPending}
        onConfirm={handleDelete}
      />
    </div>
  );
}
