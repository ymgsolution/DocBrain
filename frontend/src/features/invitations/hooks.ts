"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invitationsApi } from "./api";
import type { UserRole } from "@/types/api";

export const invitationsKeys = {
  list: () => ["invitations"] as const,
};

export function useInvitations() {
  return useQuery({ queryKey: invitationsKeys.list(), queryFn: invitationsApi.list });
}

export function useCreateInvitation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { email: string; role: UserRole; expiresInDays: number }) =>
      invitationsApi.create(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: invitationsKeys.list() }),
  });
}

export function useRevokeInvitation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => invitationsApi.revoke(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: invitationsKeys.list() }),
  });
}
