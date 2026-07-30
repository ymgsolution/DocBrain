"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { platformApi } from "./api";
import type {
  FirstAdminCreateRequest,
  OrganizationCreateRequest,
  OrganizationSettingsUpdateRequest,
  PlatformLoginRequest,
} from "./types";

export const platformKeys = {
  me: ["platform", "me"] as const,
  organizations: ["platform", "organizations"] as const,
};

export function useCurrentPlatformAdmin() {
  return useQuery({
    queryKey: platformKeys.me,
    queryFn: platformApi.me,
    retry: false,
  });
}

export function usePlatformLogin() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (payload: PlatformLoginRequest) => platformApi.login(payload),
    onSuccess: (admin) => {
      queryClient.setQueryData(platformKeys.me, admin);
      router.push("/platform");
      router.refresh();
    },
  });
}

export function usePlatformLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: () => platformApi.logout(),
    onSuccess: () => {
      queryClient.clear();
      router.push("/platform/login");
      router.refresh();
    },
    onError: () => {
      toast.error("Couldn't sign out — check your connection and try again.");
    },
  });
}

export function useOrganizations() {
  return useQuery({
    queryKey: platformKeys.organizations,
    queryFn: platformApi.listOrganizations,
  });
}

export function useCreateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OrganizationCreateRequest) => platformApi.createOrganization(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: platformKeys.organizations });
    },
  });
}

export function useCreateFirstAdmin(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: FirstAdminCreateRequest) => platformApi.createFirstAdmin(organizationId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: platformKeys.organizations });
    },
  });
}

export function useUpdateOrganizationSettings(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OrganizationSettingsUpdateRequest) =>
      platformApi.updateSettings(organizationId, payload),
    onSuccess: () => {
      // Invalidate the list rather than patching the cache by hand: the row
      // also carries storage figures this mutation doesn't return, and a
      // hand-merged cache would leave those silently stale.
      //
      // Returned, not fire-and-forget: the mutation then stays pending until
      // the refetch lands, so the dialog closes onto fresh data instead of
      // racing it. Without this, reopening straight after a save showed the
      // pre-save values.
      return queryClient.invalidateQueries({ queryKey: platformKeys.organizations });
    },
  });
}
