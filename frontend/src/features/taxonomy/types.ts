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
