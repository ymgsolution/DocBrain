import { ApiError } from "@/lib/api-client";
import type { ApiErrorBody } from "@/types/api";
import type {
  FirstAdminCreateRequest,
  FirstAdminCreated,
  OrganizationCreateRequest,
  OrganizationCreated,
  OrganizationStats,
  PlatformAdminSummary,
  PlatformLoginRequest,
} from "./types";

const PLATFORM_BFF_BASE = "/api/platform-bff";

// Deliberately not a reuse of lib/api-client.ts's apiClient — that client's
// 401 handling redirects to /login and clears the *user* session cookie,
// which is exactly wrong here. Small duplication, but it keeps the two
// session systems from ever being able to interfere with each other by
// sharing a code path.
async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T;

  const contentType = response.headers.get("content-type") ?? "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      await fetch("/api/platform-auth/logout", { method: "POST" }).catch(() => {});
      window.location.href = "/platform/login";
    }
    throw new ApiError(response.status, data as ApiErrorBody);
  }

  return data as T;
}

const platformApiClient = {
  get<T>(path: string): Promise<T> {
    return fetch(`${PLATFORM_BFF_BASE}${path}`, { credentials: "include" }).then((r) => handleResponse<T>(r));
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return fetch(`${PLATFORM_BFF_BASE}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      credentials: "include",
    }).then((r) => handleResponse<T>(r));
  },
};

export const platformApi = {
  async login(payload: PlatformLoginRequest): Promise<PlatformAdminSummary> {
    const response = await fetch("/api/platform-auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      credentials: "include",
    });
    const data = await response.json();
    if (!response.ok) {
      throw new ApiError(response.status, data as ApiErrorBody);
    }
    return data.admin as PlatformAdminSummary;
  },

  async logout(): Promise<void> {
    await fetch("/api/platform-auth/logout", { method: "POST", credentials: "include" });
  },

  me(): Promise<PlatformAdminSummary> {
    return platformApiClient.get<PlatformAdminSummary>("/auth/me");
  },

  listOrganizations(): Promise<OrganizationStats[]> {
    return platformApiClient.get<OrganizationStats[]>("/organizations");
  },

  createOrganization(payload: OrganizationCreateRequest): Promise<OrganizationCreated> {
    return platformApiClient.post<OrganizationCreated>("/organizations", payload);
  },

  createFirstAdmin(organizationId: string, payload: FirstAdminCreateRequest): Promise<FirstAdminCreated> {
    return platformApiClient.post<FirstAdminCreated>(`/organizations/${organizationId}/admins`, payload);
  },
};
