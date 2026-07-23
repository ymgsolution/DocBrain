import { apiClient } from "@/lib/api-client";
import type { PagedTrash, TrashFilters } from "./types";

export const trashApi = {
  list(filters: TrashFilters): Promise<PagedTrash> {
    return apiClient.get<PagedTrash>("/documents/trash", { ...filters });
  },
};
