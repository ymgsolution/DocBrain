"use client";

import { useQuery } from "@tanstack/react-query";
import { categoriesApi, tagsApi } from "./api";

export const taxonomyKeys = {
  categories: ["taxonomy", "categories"] as const,
  tags: ["taxonomy", "tags"] as const,
};

export function useCategories() {
  return useQuery({
    queryKey: taxonomyKeys.categories,
    queryFn: () => categoriesApi.list(),
  });
}

// The tag vocabulary is small (dozens, not thousands) — fetched once and
// filtered client-side, rather than a debounced per-keystroke server search.
export function useTags() {
  return useQuery({
    queryKey: taxonomyKeys.tags,
    queryFn: () => tagsApi.list({ limit: 100 }),
  });
}
