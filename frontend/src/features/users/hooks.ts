"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usersApi, type ListUsersParams } from "./api";
import type { UserRole } from "@/types/api";

export const usersKeys = {
  all: ["admin-users"] as const,
  list: (params: ListUsersParams) => ["admin-users", params] as const,
};

export function useAdminUsers(params: ListUsersParams) {
  return useQuery({
    queryKey: usersKeys.list(params),
    queryFn: () => usersApi.list(params),
    // Keeps the previous page on screen while the next one loads, so typing
    // in the search box doesn't flash the table empty between keystrokes.
    placeholderData: (previous) => previous,
  });
}

// All three invalidate the whole list rather than patching one row: a role
// change or deactivation can move a user out of the current filter entirely
// (deactivating while viewing "Active" should drop them from the table), and
// reconciling that by hand is more code than a refetch.
export function useDeactivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => usersApi.deactivate(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKeys.all }),
  });
}

export function useReactivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => usersApi.reactivate(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKeys.all }),
  });
}

export function useChangeUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, role }: { id: string; role: UserRole }) => usersApi.changeRole(id, role),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKeys.all }),
  });
}
