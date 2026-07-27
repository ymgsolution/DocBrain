"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { sharesApi } from "./api";

export const sharesKeys = {
  list: (documentId: string) => ["shares", documentId] as const,
};

export function useShareLinks(documentId: string, enabled: boolean) {
  return useQuery({
    queryKey: sharesKeys.list(documentId),
    queryFn: () => sharesApi.list(documentId),
    // Only fetched while the share dialog is actually open — there's no
    // reason for every document page view to ask about share links.
    enabled,
  });
}

export function useCreateShareLink(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (expiresInDays: number) => sharesApi.create(documentId, expiresInDays),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sharesKeys.list(documentId) }),
  });
}

export function useRevokeShareLink(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (linkId: string) => sharesApi.revoke(documentId, linkId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sharesKeys.list(documentId) }),
  });
}
