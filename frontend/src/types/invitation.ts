import type { UserRole } from "@/types/api";
import type { UserSummary } from "@/features/auth/types";

export type InvitationStatus = "pending" | "accepted" | "revoked" | "expired";

export interface InvitationSummary {
  id: string;
  email: string;
  role: UserRole;
  status: InvitationStatus;
  expiresAt: string;
  createdAt: string;
  acceptedAt: string | null;
  invitedBy: UserSummary;
}

// Only ever returned by the create call — the raw token is unrecoverable
// afterwards, so this is the single moment the link can be copied.
export interface InvitationCreated extends InvitationSummary {
  token: string;
  url: string;
}

// What the accept page may show before anyone proves anything.
export interface PublicInvitation {
  email: string;
  role: UserRole;
  expiresAt: string;
}
