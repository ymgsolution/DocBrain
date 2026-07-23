import { ApiError, apiClient } from "@/lib/api-client";
import type { ApiErrorBody } from "@/types/api";
import type { LoginRequest, UserSummary } from "./types";

export const authApi = {
  // Login is special-cased (not routed through /api/bff) because the BFF
  // proxy's job is attaching an *existing* cookie — login is what creates it.
  async login(payload: LoginRequest): Promise<UserSummary> {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      credentials: "include",
    });
    const data = await response.json();
    if (!response.ok) {
      throw new ApiError(response.status, data as ApiErrorBody);
    }
    return data.user as UserSummary;
  },

  async logout(): Promise<void> {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
  },

  me(): Promise<UserSummary> {
    return apiClient.get<UserSummary>("/auth/me");
  },

  listPersonas(): Promise<UserSummary[]> {
    return apiClient.get<UserSummary[]>("/auth/users");
  },
};
