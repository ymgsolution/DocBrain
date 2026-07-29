import type { UserRole } from "@/types/api";

export interface OrganizationSummary {
  id: string;
  name: string;
  slug: string;
}

export interface UserSummary {
  id: string;
  displayName: string;
  email: string;
  role: UserRole;
  // Nullable until the backend's Phase 4 migration makes organization_id
  // required on every user — see docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md.
  organization: OrganizationSummary | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export type ThemePreference = "light" | "dark" | "system";

export interface UserPreferences {
  theme: ThemePreference;
  defaultPageSize: number;
}

export interface UserPreferencesUpdate {
  theme?: ThemePreference;
  defaultPageSize?: number;
}
