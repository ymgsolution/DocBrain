"use client";

import { useQuery } from "@tanstack/react-query";
import { reviewsApi } from "./api";
import type { PendingReviewsFilters } from "./types";

export const reviewsKeys = {
  pending: (filters: PendingReviewsFilters) => ["reviews", "pending", filters] as const,
};

export function usePendingReviews(filters: PendingReviewsFilters) {
  return useQuery({
    queryKey: reviewsKeys.pending(filters),
    queryFn: () => reviewsApi.listPending(filters),
    placeholderData: (previousData) => previousData,
  });
}
