import type { DocumentSummary, ReviewStatus } from "@/types/document";

export type DocumentSort = "updated_at" | "created_at" | "title";

export interface DocumentListFilters {
  q?: string;
  categoryId?: string;
  tagId?: string[];
  ownerId?: string;
  reviewStatus?: ReviewStatus;
  sort?: DocumentSort;
  page: number;
  size: number;
}

export interface PagedDocuments {
  items: DocumentSummary[];
  page: number;
  size: number;
  total: number;
  totalPages: number;
}
