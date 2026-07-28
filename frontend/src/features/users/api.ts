import { apiClient } from "@/lib/api-client";
import type { AdminUser, PagedUsers, UserStatusFilter } from "@/types/user-admin";
import type { UserRole } from "@/types/api";

export interface ListUsersParams {
  search?: string;
  status?: UserStatusFilter;
  page?: number;
  size?: number;
}

export const usersApi = {
  list({ search, status = "active", page = 0, size = 25 }: ListUsersParams = {}): Promise<PagedUsers> {
    const params = new URLSearchParams({ status, page: String(page), size: String(size) });
    if (search) params.set("search", search);
    return apiClient.get<PagedUsers>(`/admin/users?${params.toString()}`);
  },

  // Two named actions rather than one PATCH { isActive }: deactivating is
  // guarded and has side effects (it kills the person's outstanding reset
  // links and share links), reactivating is a plain flip. Mirrors the API.
  deactivate(id: string): Promise<AdminUser> {
    return apiClient.post<AdminUser>(`/admin/users/${id}/deactivate`, {});
  },

  reactivate(id: string): Promise<AdminUser> {
    return apiClient.post<AdminUser>(`/admin/users/${id}/reactivate`, {});
  },

  changeRole(id: string, role: UserRole): Promise<AdminUser> {
    return apiClient.patch<AdminUser>(`/admin/users/${id}/role`, { role });
  },
};
