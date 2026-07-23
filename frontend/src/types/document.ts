import type { UserSummary } from "@/features/auth/types";

export type ReviewStatus = "ok" | "due_soon" | "overdue";

export interface CategorySummary {
  id: string;
  name: string;
  slug: string;
}

export interface TagSummary {
  id: string;
  name: string;
}

export interface VersionSummary {
  id: string;
  versionNumber: number;
  originalFilename: string;
  sizeBytes: number;
  mimeType: string;
  uploadedAt: string;
}

export interface DocumentSummary {
  id: string;
  title: string;
  description: string | null;
  category: CategorySummary;
  owner: UserSummary;
  currentVersion: VersionSummary | null;
  versionCount: number;
  reviewDueDate: string | null;
  updatedAt: string;
  createdAt: string;
}

export interface DocumentDetail extends DocumentSummary {
  tags: TagSummary[];
  lastReviewedAt: string | null;
  lastAccessedAt: string | null;
  status: "ACTIVE" | "DELETED";
}
