import type { CategorySummary, ReviewStatus } from "@/types/document";
import type { UserSummary } from "@/features/auth/types";

export interface PendingReviewItem {
  id: string;
  title: string;
  category: CategorySummary;
  owner: UserSummary;
  reviewDueDate: string;
  reviewStatus: Extract<ReviewStatus, "due_soon" | "overdue">;
  daysOverdue: number;
}

export interface PagedPendingReviews {
  items: PendingReviewItem[];
  page: number;
  size: number;
  total: number;
  totalPages: number;
}

export interface PendingReviewsFilters {
  categoryId?: string;
  ownerId?: string;
  page: number;
  size: number;
}
