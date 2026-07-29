"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { platformApi } from "./api";
import type { FirstAdminCreateRequest, OrganizationCreateRequest, PlatformLoginRequest } from "./types";

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
