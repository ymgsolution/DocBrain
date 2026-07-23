"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { authApi } from "./api";
import type { LoginRequest, UserPreferencesUpdate } from "./types";

export const authKeys = {
  me: ["auth", "me"] as const,
  personas: ["auth", "personas"] as const,
  preferences: ["auth", "preferences"] as const,
};

export function useCurrentUser() {
  return useQuery({
    queryKey: authKeys.me,
    queryFn: authApi.me,
    retry: false,
  });
}

export function usePersonas() {
  return useQuery({
    queryKey: authKeys.personas,
    queryFn: authApi.listPersonas,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (payload: LoginRequest) => authApi.login(payload),
    onSuccess: (user) => {
      queryClient.setQueryData(authKeys.me, user);
      router.push("/");
      router.refresh();
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      queryClient.clear();
      router.push("/login");
      router.refresh();
    },
    // authApi.logout() can still reject on a genuine network failure (the
    // fetch itself throwing) — without this, that case failed silently with
    // no feedback at all.
    onError: () => {
      toast.error("Couldn't sign out — check your connection and try again.");
    },
  });
}

export function usePreferences() {
  return useQuery({
    queryKey: authKeys.preferences,
    queryFn: authApi.getPreferences,
  });
}

export function useUpdatePreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UserPreferencesUpdate) => authApi.updatePreferences(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(authKeys.preferences, data);
    },
  });
}
