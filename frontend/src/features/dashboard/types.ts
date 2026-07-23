import type { DocumentSummary } from "@/types/document";

export interface DashboardTotals {
  totalDocuments: number;
  uploadedThisWeek: number;
  versionsTracked: number;
  categoriesInUse: number;
}

export interface CategoryCount {
  categoryId: string;
  categoryName: string;
  documentCount: number;
}

export interface DashboardSummary {
  totals: DashboardTotals;
  byCategory: CategoryCount[];
  recentlyAdded: DocumentSummary[];
  recentlyAccessed: DocumentSummary[];
  expiringSoon: DocumentSummary[];
  pendingReviewsCount: number;
}

export interface ActivityEvent {
  id: string;
  documentId: string | null;
  documentTitle: string | null;
  actorName: string;
  eventType: string;
  summary: string;
  occurredAt: string;
}

export interface PagedActivity {
  items: ActivityEvent[];
  page: number;
  size: number;
  total: number;
  totalPages: number;
}
