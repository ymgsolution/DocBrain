"use client";

import { AppBreadcrumb } from "@/components/layout/app-breadcrumb";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState } from "@/components/shared/error-state";
import { ReviewStatusBadge } from "@/components/shared/status-badge";
import { useCurrentUser } from "@/features/auth/hooks";
import { useDashboardActivity, useDashboardSummary } from "@/features/dashboard/hooks";
import { KpiSection, KpiSectionSkeleton } from "@/features/dashboard/components/kpi-section";
import { CategoryDistribution } from "@/features/dashboard/components/category-distribution";
import { DocumentListCard } from "@/features/dashboard/components/document-list-card";
import { ActivityFeed } from "@/features/dashboard/components/activity-feed";
import { PendingReviewsBanner } from "@/features/dashboard/components/pending-reviews-banner";
import { WidgetSkeleton } from "@/features/dashboard/components/widget-skeleton";
import { getReviewStatus, formatRelativeTime } from "@/lib/format";
import { ApiError } from "@/lib/api-client";
import { REVIEWER_ROLES } from "@/components/layout/nav-items";
import { FilePlus, FolderOpen, ClipboardCheck } from "lucide-react";

export default function DashboardPage() {
  const { data: user } = useCurrentUser();
  const summary = useDashboardSummary();
  const activity = useDashboardActivity();

  const firstName = user?.displayName.split(" ")[0];

  return (
    <div className="space-y-6">
      <AppBreadcrumb segments={[{ label: "Dashboard" }]} />
      <PageHeader
        title={firstName ? `Welcome back, ${firstName}` : "Dashboard"}
        description="Here's what's happening across your document library."
      />

      {summary.isError ? (
        <ErrorState
          message={summary.error instanceof ApiError ? summary.error.message : "Couldn't load the dashboard."}
          correlationId={summary.error instanceof ApiError ? summary.error.correlationId : undefined}
          onRetry={() => summary.refetch()}
        />
      ) : summary.isLoading || !summary.data ? (
        <KpiSectionSkeleton />
      ) : (
        <>
          <KpiSection totals={summary.data.totals} />

          {user && REVIEWER_ROLES.includes(user.role) && (
            <PendingReviewsBanner count={summary.data.pendingReviewsCount} />
          )}

          <div className="grid gap-4 lg:grid-cols-3">
            <CategoryDistribution byCategory={summary.data.byCategory} />
            <DocumentListCard
              title="Recently Added"
              icon={FilePlus}
              documents={summary.data.recentlyAdded}
              emptyTitle="No documents uploaded yet"
              viewAllHref="/documents?sort=recent"
              meta={(document) => `${document.category.name} · ${formatRelativeTime(document.createdAt)}`}
            />
            <DocumentListCard
              title="Recently Accessed"
              icon={FolderOpen}
              documents={summary.data.recentlyAccessed}
              emptyTitle="No documents opened yet"
              viewAllHref="/documents"
              meta={(document) => `${document.category.name} · ${formatRelativeTime(document.updatedAt)}`}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <DocumentListCard
              title="Expiring Soon"
              icon={ClipboardCheck}
              documents={summary.data.expiringSoon}
              emptyTitle="Nothing due for review"
              viewAllHref="/documents?reviewStatus=due_soon"
              meta={(document) => document.category.name}
              trailing={(document) => <ReviewStatusBadge status={getReviewStatus(document.reviewDueDate)} />}
            />

            {activity.isError ? (
              <ErrorState
                title="Couldn't load activity"
                message={activity.error instanceof ApiError ? activity.error.message : undefined}
                correlationId={activity.error instanceof ApiError ? activity.error.correlationId : undefined}
                onRetry={() => activity.refetch()}
              />
            ) : activity.isLoading || !activity.data ? (
              <WidgetSkeleton />
            ) : (
              <ActivityFeed events={activity.data.items} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
