"use client";

import { useQuery } from "@tanstack/react-query";
import { trashApi } from "./api";
import type { TrashFilters } from "./types";

export const trashKeys = {
  list: (filters: TrashFilters) => ["trash", "list", filters] as const,
};

export function useTrash(filters: TrashFilters) {
  return useQuery({
    queryKey: trashKeys.list(filters),
    queryFn: () => trashApi.list(filters),
    placeholderData: (previousData) => previousData,
  });
}
