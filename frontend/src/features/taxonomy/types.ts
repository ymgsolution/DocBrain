export interface Category {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  defaultReviewPeriodDays: number | null;
  isArchived: boolean;
  documentCount: number;
}

export interface Tag {
  id: string;
  name: string;
  usageCount: number;
}

export interface CategoryCreatePayload {
  name: string;
  description?: string;
  defaultReviewPeriodDays?: number;
}

export interface CategoryUpdatePayload {
  name?: string;
  description?: string;
  defaultReviewPeriodDays?: number;
  isArchived?: boolean;
}

export interface TagMergeResponse {
  documentsUpdated: number;
}
