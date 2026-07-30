import type { UserRole } from "@/types/api";

export interface OrganizationSummary {
  id: string;
  name: string;
  slug: string;
  // Organization Settings — read-only here. Only a platform admin can change
  // them, under /platform. They ride along with the user because
  // User.organization is already eager-loaded on every request, so the app
  // has them on first paint with no extra call.
  //
  // These exist because empty results are ambiguous: a null aiSuggestion
  // means either "the worker hasn't finished" or "suggestions are switched
  // off", and isAiSuggestionPending() in lib/format.ts has to tell those
  // apart or it will poll and show "Getting AI suggestions…" forever.
  aiSuggestionsEnabled: boolean;
  duplicateDetectionEnabled: boolean;
}

export interface UserSummary {
  id: string;
  displayName: string;
  email: string;
  role: UserRole;
  // Optional on the wire even though organization_id has been NOT NULL since
  // the Phase 4 migration: this type is nested inside version, trash and
  // admin responses whose backend queries don't all eager-load the
  // relationship. Mirrors the Pydantic schema exactly.
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
