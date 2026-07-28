import type { UserRole } from "@/types/api";

export interface UserSummary {
  id: string;
  displayName: string;
  email: string;
  role: UserRole;
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
