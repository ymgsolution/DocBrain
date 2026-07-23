import { apiClient } from "@/lib/api-client";
import type { Category, Tag } from "./types";

export const categoriesApi = {
  list(params?: { includeArchived?: boolean }): Promise<Category[]> {
    return apiClient.get<Category[]>("/categories", params);
  },
};

export const tagsApi = {
  list(params?: { q?: string; limit?: number }): Promise<Tag[]> {
    return apiClient.get<Tag[]>("/tags", params);
  },
};
