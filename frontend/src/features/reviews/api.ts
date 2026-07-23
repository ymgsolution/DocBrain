import { apiClient } from "@/lib/api-client";
import type { PagedPendingReviews, PendingReviewsFilters } from "./types";

export const reviewsApi = {
  listPending(filters: PendingReviewsFilters): Promise<PagedPendingReviews> {
    return apiClient.get<PagedPendingReviews>("/reviews/pending", { ...filters });
  },
};
