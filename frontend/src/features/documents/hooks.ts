"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { documentsApi } from "./api";
import type { DocumentCreatePayload, DocumentListFilters } from "./types";

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

export function useCreateDocument() {
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState(0);

  const mutation = useMutation({
    mutationFn: (payload: DocumentCreatePayload) => {
      setProgress(0);
      return documentsApi.create(payload, setProgress);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  return { ...mutation, progress };
}
