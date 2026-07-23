"use client";

import { useQuery } from "@tanstack/react-query";
import { documentsApi } from "./api";
import type { DocumentListFilters } from "./types";

export const documentsKeys = {
  list: (filters: DocumentListFilters) => ["documents", "list", filters] as const,
};

export function useDocuments(filters: DocumentListFilters) {
  return useQuery({
    queryKey: documentsKeys.list(filters),
    queryFn: () => documentsApi.list(filters),
    placeholderData: (previousData) => previousData,
  });
}
