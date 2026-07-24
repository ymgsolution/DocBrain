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

// AI feature track — null means no extraction row exists yet (the
// background job hasn't been claimed by the worker), treated identically to
// PENDING: still show the "Analyzing…" indicator.
export type ExtractionStatus = "PENDING" | "SUCCEEDED" | "FAILED" | "UNSUPPORTED" | null;

// AI feature track (Phase 2) — null whenever there's nothing to show yet (no
// job run, still pending, or it failed); the UI simply omits the card.
export interface AiSuggestion {
  title: string | null;
  summary: string | null;
  tags: string[];
}

export interface DocumentDetail extends DocumentSummary {
  tags: TagSummary[];
  lastReviewedAt: string | null;
  lastAccessedAt: string | null;
  status: "ACTIVE" | "DELETED";
  extractionStatus: ExtractionStatus;
  aiSuggestion: AiSuggestion | null;
}

export interface VersionDetail {
  id: string;
  versionNumber: number;
  isCurrent: boolean;
  originalFilename: string;
  mimeType: string;
  sizeBytes: number;
  checksumSha256: string;
  changeNote: string | null;
  uploadedBy: UserSummary;
  uploadedAt: string;
  restoredFromVersionId: string | null;
}
