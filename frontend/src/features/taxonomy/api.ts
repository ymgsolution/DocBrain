import { apiClient } from "@/lib/api-client";
import type { Category, CategoryCreatePayload, CategoryUpdatePayload, Tag, TagMergeResponse } from "./types";

export const categoriesApi = {
  list(params?: { includeArchived?: boolean }): Promise<Category[]> {
    return apiClient.get<Category[]>("/categories", params);
  },

  create(payload: CategoryCreatePayload): Promise<Category> {
    return apiClient.post<Category>("/categories", payload);
  },

  update(id: string, payload: CategoryUpdatePayload): Promise<Category> {
    return apiClient.patch<Category>(`/categories/${id}`, payload);
  },

  delete(id: string): Promise<void> {
    return apiClient.delete<void>(`/categories/${id}`);
  },
};

export const tagsApi = {
  list(params?: { q?: string; limit?: number }): Promise<Tag[]> {
    return apiClient.get<Tag[]>("/tags", params);
  },

  rename(id: string, name: string): Promise<Tag> {
    return apiClient.patch<Tag>(`/tags/${id}`, { name });
  },

  merge(id: string, targetTagId: string): Promise<TagMergeResponse> {
    return apiClient.post<TagMergeResponse>(`/tags/${id}/merge`, { targetTagId });
  },

  delete(id: string): Promise<void> {
    return apiClient.delete<void>(`/tags/${id}`);
  },
};
