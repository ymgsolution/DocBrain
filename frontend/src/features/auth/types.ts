import type { UserRole } from "@/types/api";

export interface UserSummary {
  id: string;
  displayName: string;
  email: string;
  role: UserRole;
}

export interface LoginRequest {
  email: string;
}
