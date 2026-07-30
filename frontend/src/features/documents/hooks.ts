"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { documentsApi } from "./api";
import { dashboardApi } from "@/features/dashboard/api";
import { useCurrentUser } from "@/features/auth/hooks";
import { isExtractionPending, isAiSuggestionPending } from "@/lib/format";
import type { DocumentCreatePayload, DocumentListFilters, DocumentUpdatePayload } from "./types";

export const documentsKeys = {
  list: (filters: DocumentListFilters) => ["documents", "list", filters] as const,
  detail: (id: string) => ["documents", "detail", id] as const,
  versions: (id: string) => ["documents", "versions", id] as const,
  activity: (id: string) => ["documents", "activity", id] as const,
  similar: (id: string) => ["documents", "similar", id] as const,
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

export function useDocument(id: string) {
  // Read here and closed over below: refetchInterval is a plain callback, not
  // a component, so it can't call a hook itself.
  const { data: user } = useCurrentUser();
  const aiSuggestionsEnabled = user?.organization?.aiSuggestionsEnabled ?? false;

  return useQuery({
    queryKey: documentsKeys.detail(id),
    queryFn: () => documentsApi.get(id),
    // AI feature track — poll while extraction hasn't finished yet, so the
    // "Analyzing…" badge clears on its own; stops the instant it lands on a
    // terminal status, or after isExtractionPending's own timeout (worker
    // down / job stuck) so this never polls forever.
    //
    // Defaulting to false while the user query is still loading is
    // deliberate: at worst the first poll is skipped and the next render
    // starts it, which is far better than polling for two minutes against an
    // organization that will never produce a suggestion.
    refetchInterval: (query) => {
      const data = query.state.data;
      return data && (isExtractionPending(data) || isAiSuggestionPending(data, aiSuggestionsEnabled))
        ? 2000
        : false;
    },
  });
}

export function useDocumentVersions(id: string) {
  return useQuery({
    queryKey: documentsKeys.versions(id),
    queryFn: () => documentsApi.listVersions(id),
  });
}

export function useReviewAiSuggestion(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => documentsApi.reviewAiSuggestion(id),
    onSuccess: () => invalidateAfterDocumentChange(queryClient, id),
  });
}

export function useSimilarDocuments(id: string) {
  return useQuery({
    queryKey: documentsKeys.similar(id),
    queryFn: () => documentsApi.listSimilar(id),
  });
}

export function useDocumentActivity(id: string) {
  return useQuery({
    queryKey: documentsKeys.activity(id),
    queryFn: () => dashboardApi.getActivity({ documentId: id, size: 50 }),
  });
}

function invalidateAfterDocumentChange(queryClient: ReturnType<typeof useQueryClient>, id: string) {
  queryClient.invalidateQueries({ queryKey: documentsKeys.detail(id) });
  queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  // Marking reviewed / soft-deleting / restoring a document can change its
  // membership in either queue, so both are kept in lockstep with every
  // document mutation rather than each call site remembering to do it.
  queryClient.invalidateQueries({ queryKey: ["reviews"] });
  queryClient.invalidateQueries({ queryKey: ["trash"] });
}

export function useUpdateDocument(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DocumentUpdatePayload) => documentsApi.update(id, payload),
    onSuccess: () => invalidateAfterDocumentChange(queryClient, id),
  });
}

export function useMarkReviewed(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (note: string | undefined) => documentsApi.markReviewed(id, note),
    onSuccess: () => invalidateAfterDocumentChange(queryClient, id),
  });
}

export function useSoftDeleteDocument(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => documentsApi.softDelete(id),
    onSuccess: () => invalidateAfterDocumentChange(queryClient, id),
  });
}

export function useRestoreDocument(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => documentsApi.restore(id),
    onSuccess: () => invalidateAfterDocumentChange(queryClient, id),
  });
}

export function useHardDeleteDocument(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => documentsApi.hardDelete(id),
    onSuccess: () => invalidateAfterDocumentChange(queryClient, id),
  });
}

function invalidateAfterVersionChange(queryClient: ReturnType<typeof useQueryClient>, id: string) {
  queryClient.invalidateQueries({ queryKey: documentsKeys.versions(id) });
  queryClient.invalidateQueries({ queryKey: documentsKeys.activity(id) });
  invalidateAfterDocumentChange(queryClient, id);
}

export function useUploadVersion(id: string) {
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState(0);

  const mutation = useMutation({
    mutationFn: ({ file, changeNote }: { file: File; changeNote: string }) => {
      setProgress(0);
      return documentsApi.uploadVersion(id, file, changeNote, setProgress);
    },
    onSuccess: () => invalidateAfterVersionChange(queryClient, id),
  });

  return { ...mutation, progress };
}

export function useRestoreVersion(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (versionNumber: number) => documentsApi.restoreVersion(id, versionNumber),
    onSuccess: () => invalidateAfterVersionChange(queryClient, id),
  });
}
