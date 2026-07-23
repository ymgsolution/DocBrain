"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { categoriesApi, tagsApi } from "./api";
import type { CategoryCreatePayload, CategoryUpdatePayload } from "./types";

export const taxonomyKeys = {
  categories: (includeArchived: boolean) => ["taxonomy", "categories", includeArchived] as const,
  tags: ["taxonomy", "tags"] as const,
};

export function useCategories(includeArchived = false) {
  return useQuery({
    queryKey: taxonomyKeys.categories(includeArchived),
    queryFn: () => categoriesApi.list({ includeArchived }),
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

function invalidateCategories(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["taxonomy", "categories"] });
}

export function useCreateCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CategoryCreatePayload) => categoriesApi.create(payload),
    onSuccess: () => invalidateCategories(queryClient),
  });
}

export function useUpdateCategory(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CategoryUpdatePayload) => categoriesApi.update(id, payload),
    onSuccess: () => invalidateCategories(queryClient),
  });
}

export function useDeleteCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => categoriesApi.delete(id),
    onSuccess: () => invalidateCategories(queryClient),
  });
}

function invalidateTags(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: taxonomyKeys.tags });
}

export function useRenameTag(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => tagsApi.rename(id, name),
    onSuccess: () => invalidateTags(queryClient),
  });
}

export function useMergeTag(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (targetTagId: string) => tagsApi.merge(id, targetTagId),
    onSuccess: () => invalidateTags(queryClient),
  });
}

export function useDeleteTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => tagsApi.delete(id),
    onSuccess: () => invalidateTags(queryClient),
  });
}
