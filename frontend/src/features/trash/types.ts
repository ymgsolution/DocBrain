import type { CategorySummary } from "@/types/document";
import type { UserSummary } from "@/features/auth/types";

export interface TrashedDocumentItem {
  id: string;
  title: string;
  category: CategorySummary;
  owner: UserSummary;
  deletedAt: string;
  deletedBy: UserSummary | null;
}

export interface PagedTrash {
  items: TrashedDocumentItem[];
  page: number;
  size: number;
  total: number;
  totalPages: number;
}

export interface TrashFilters {
  page: number;
  size: number;
}
