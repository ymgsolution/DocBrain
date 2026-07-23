"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ClipboardCheck } from "lucide-react";
import { AppBreadcrumb } from "@/components/layout/app-breadcrumb";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { ForbiddenState } from "@/components/shared/forbidden-state";
import { PaginationBar } from "@/components/shared/pagination-bar";
import { ReviewStatusBadge } from "@/components/shared/status-badge";
import { UserAvatar } from "@/components/shared/user-avatar";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCurrentUser, usePersonas } from "@/features/auth/hooks";
import { useCategories } from "@/features/taxonomy/hooks";
import { usePendingReviews } from "@/features/reviews/hooks";
import { MarkReviewedDialog } from "@/features/documents/components/mark-reviewed-dialog";
import { ApiError } from "@/lib/api-client";
import type { PendingReviewItem } from "@/features/reviews/types";

const PAGE_SIZE = 25;

export default function PendingReviewsPage() {
  const { data: user, isLoading: userLoading } = useCurrentUser();

  const [categoryId, setCategoryId] = useState<string | undefined>(undefined);
  const [ownerId, setOwnerId] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(0);
  const [reviewingId, setReviewingId] = useState<string | null>(null);

  const filters = useMemo(
    () => ({ categoryId, ownerId, page, size: PAGE_SIZE }),
    [categoryId, ownerId, page],
  );
  const { data, isLoading, isError, error, refetch } = usePendingReviews(filters);
  const { data: categories } = useCategories();
  const { data: personas } = usePersonas();

  if (userLoading) {
    return <Skeleton className="h-64 w-full rounded-lg" />;
  }

  if (user && user.role !== "REVIEWER" && user.role !== "ADMIN") {
    return (
      <div className="space-y-6">
        <AppBreadcrumb segments={[{ label: "Pending Reviews" }]} />
        <ForbiddenState requiredRole="Reviewer or Admin" />
      </div>
    );
  }

  const categoryLabels: Record<string, string> = { all: "All Categories" };
  categories?.forEach((c) => (categoryLabels[c.id] = c.name));
  const ownerLabels: Record<string, string> = { all: "All Owners" };
  personas?.forEach((p) => (ownerLabels[p.id] = p.displayName));

  return (
    <div className="space-y-6">
      <AppBreadcrumb segments={[{ label: "Pending Reviews" }]} />
      <PageHeader
        title="Pending Reviews"
        description="Documents due or overdue for review, soonest first."
      />

      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={categoryId ?? "all"}
          onValueChange={(value) => {
            setCategoryId(value === "all" || !value ? undefined : value);
            setPage(0);
          }}
        >
          <SelectTrigger size="sm" className="w-44">
            <SelectValue placeholder="All Categories">
              {(value: string) => categoryLabels[value] ?? "All Categories"}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories?.map((category) => (
              <SelectItem key={category.id} value={category.id}>
                {category.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={ownerId ?? "all"}
          onValueChange={(value) => {
            setOwnerId(value === "all" || !value ? undefined : value);
            setPage(0);
          }}
        >
          <SelectTrigger size="sm" className="w-44">
            <SelectValue placeholder="All Owners">
              {(value: string) => ownerLabels[value] ?? "All Owners"}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Owners</SelectItem>
            {personas?.map((persona) => (
              <SelectItem key={persona.id} value={persona.id}>
                {persona.displayName}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isError ? (
        <ErrorState
          message={error instanceof ApiError ? error.message : "Couldn't load pending reviews."}
          correlationId={error instanceof ApiError ? error.correlationId : undefined}
          onRetry={() => refetch()}
        />
      ) : isLoading || !data ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-14 w-full rounded-lg" />
          ))}
        </div>
      ) : data.items.length === 0 ? (
        <EmptyState icon={ClipboardCheck} title="Nothing due for review right now." />
      ) : (
        <>
          <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Title</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead>Due date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((item) => (
                  <ReviewRow key={item.id} item={item} onMarkReviewed={() => setReviewingId(item.id)} />
                ))}
              </TableBody>
            </Table>
          </div>
          <PaginationBar
            page={data.page}
            size={data.size}
            total={data.total}
            totalPages={data.totalPages}
            onPageChange={setPage}
          />
        </>
      )}

      {reviewingId && (
        <MarkReviewedDialog
          documentId={reviewingId}
          open={Boolean(reviewingId)}
          onOpenChange={(open) => !open && setReviewingId(null)}
        />
      )}
    </div>
  );
}

function ReviewRow({ item, onMarkReviewed }: { item: PendingReviewItem; onMarkReviewed: () => void }) {
  return (
    <TableRow>
      <TableCell className="max-w-xs">
        <Link href={`/documents/${item.id}`} className="hover:text-primary truncate text-sm font-medium">
          {item.title}
        </Link>
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">{item.category.name}</TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <UserAvatar name={item.owner.displayName} className="size-6" />
          <span className="text-sm">{item.owner.displayName}</span>
        </div>
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">
        {item.reviewDueDate}
        {item.daysOverdue > 0 && (
          <span className="text-destructive ml-1.5">
            ({item.daysOverdue} day{item.daysOverdue === 1 ? "" : "s"} overdue)
          </span>
        )}
      </TableCell>
      <TableCell>
        <ReviewStatusBadge status={item.reviewStatus} />
      </TableCell>
      <TableCell className="text-right">
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" nativeButton={false} render={<Link href={`/documents/${item.id}`} />}>
            Open
          </Button>
          <Button size="sm" onClick={onMarkReviewed}>
            Mark as reviewed
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}
