import type { UserRole } from "@/types/api";
import type { UserSummary } from "@/features/auth/types";

export type UserStatusFilter = "active" | "inactive" | "all";

// Strictly wider than UserSummary (the colleague directory's shape): only the
// admin endpoints return isActive and the deactivation audit pair, which is
// why this lives in its own type rather than extending the shared one.
export interface AdminUser {
  id: string;
  displayName: string;
  email: string;
  role: UserRole;
  isActive: boolean;
  createdAt: string;
  deactivatedAt: string | null;
  deactivatedBy: UserSummary | null;
}

export interface PagedUsers {
  items: AdminUser[];
  page: number;
  size: number;
  total: number;
  totalPages: number;
}
