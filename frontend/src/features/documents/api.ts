import { apiClient } from "@/lib/api-client";
import type { DocumentListFilters, PagedDocuments } from "./types";

export const documentsApi = {
  list(filters: DocumentListFilters): Promise<PagedDocuments> {
    return apiClient.get<PagedDocuments>("/documents", { ...filters });
  },
};
