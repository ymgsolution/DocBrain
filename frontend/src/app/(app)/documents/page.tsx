"use client";

import { Suspense, useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { FileX2 } from "lucide-react";
import { AppBreadcrumb } from "@/components/layout/app-breadcrumb";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PaginationBar } from "@/components/shared/pagination-bar";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client";
import { useDocuments } from "@/features/documents/hooks";
import { DocumentFilters } from "@/features/documents/components/document-filters";
import { DocumentsTable } from "@/features/documents/components/documents-table";
import { DocumentsMobileList } from "@/features/documents/components/documents-mobile-list";
import type { DocumentListFilters, DocumentSort } from "@/features/documents/types";
import type { ReviewStatus } from "@/types/document";

const PAGE_SIZE = 25;

function parseFilters(searchParams: URLSearchParams): DocumentListFilters {
  return {
    q: searchParams.get("q") ?? undefined,
    categoryId: searchParams.get("categoryId") ?? undefined,
    tagId: searchParams.getAll("tagId"),
    reviewStatus: (searchParams.get("reviewStatus") as ReviewStatus | null) ?? undefined,
    sort: (searchParams.get("sort") as DocumentSort | null) ?? undefined,
    page: Number(searchParams.get("page") ?? 0),
    size: PAGE_SIZE,
  };
}

export default function DocumentExplorerPage() {
  return (
    <Suspense fallback={<ExplorerSkeleton />}>
      <DocumentExplorer />
    </Suspense>
  );
}

function ExplorerSkeleton() {
  return (
    <div className="space-y-6">
      <AppBreadcrumb segments={[{ label: "Documents" }]} />
      <PageHeader title="Documents" description="Browse, search, and filter your organization's document library." />
      <div className="space-y-2">
        {Array.from({ length: 8 }, (_, i) => (
          <Skeleton key={i} className="h-14 w-full rounded-lg" />
        ))}
      </div>
    </div>
  );
}

function DocumentExplorer() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const filters = useMemo(() => parseFilters(searchParams), [searchParams]);

  const updateFilters = useCallback(
    (patch: Partial<DocumentListFilters>) => {
      const next = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(patch)) {
        if (key === "tagId") {
          next.delete("tagId");
          (value as string[] | undefined)?.forEach((tagId) => next.append("tagId", tagId));
          continue;
        }
        if (value === undefined || value === null || value === "") {
          next.delete(key);
        } else {
          next.set(key, String(value));
        }
      }
      if (!("page" in patch)) next.delete("page");
      router.push(`${pathname}?${next.toString()}`);
    },
    [pathname, router, searchParams],
  );

  const { data, isLoading, isError, error, refetch } = useDocuments(filters);
  const hasActiveFilters = Boolean(
    filters.q || filters.categoryId || filters.reviewStatus || filters.tagId?.length,
  );

  return (
    <div className="space-y-6">
      <AppBreadcrumb segments={[{ label: "Documents" }]} />
      <PageHeader title="Documents" description="Browse, search, and filter your organization's document library." />

      <DocumentFilters filters={filters} onChange={updateFilters} />

      {isError ? (
        <ErrorState
          message={error instanceof ApiError ? error.message : "Couldn't load documents."}
          correlationId={error instanceof ApiError ? error.correlationId : undefined}
          onRetry={() => refetch()}
        />
      ) : isLoading || !data ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="h-14 w-full rounded-lg" />
          ))}
        </div>
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={FileX2}
          title={hasActiveFilters ? "No documents match these filters" : "No documents yet"}
          description={
            hasActiveFilters
              ? "Try adjusting or clearing your search and filters."
              : "Documents your organization uploads will show up here."
          }
        />
      ) : (
        <>
          <div className="hidden lg:block">
            <DocumentsTable documents={data.items} />
          </div>
          <div className="lg:hidden">
            <DocumentsMobileList documents={data.items} />
          </div>
          <PaginationBar
            page={data.page}
            size={data.size}
            total={data.total}
            totalPages={data.totalPages}
            onPageChange={(page) => updateFilters({ page })}
          />
        </>
      )}
    </div>
  );
}
