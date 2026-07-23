import { apiClient } from "@/lib/api-client";
import type { Category, CategoryCreatePayload, CategoryUpdatePayload, Tag } from "./types";

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
};
