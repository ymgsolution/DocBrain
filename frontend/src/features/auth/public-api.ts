import { ApiError } from "@/lib/api-client";
import type { ApiErrorBody } from "@/types/api";
import type { PublicInvitation } from "@/types/invitation";
import type { UserSummary } from "./types";

// These four calls deliberately bypass /api/bff. That proxy's job is
// attaching an existing session cookie, and every request here is made by
// someone who has no session — an invitee creating their account, or
// someone who's forgotten their password. Routing them through the BFF
// would attach whatever cookie happened to be present, which is both
// meaningless and misleading.
async function publicRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/public${path}`, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, data as ApiErrorBody);
  return data as T;
}

export const publicAuthApi = {
  getInvitation(token: string): Promise<PublicInvitation> {
    return publicRequest<PublicInvitation>(`/invitations/${encodeURIComponent(token)}`);
  },

  acceptInvitation(token: string, payload: { displayName: string; password: string }): Promise<UserSummary> {
    return publicRequest<UserSummary>(`/invitations/${encodeURIComponent(token)}/accept`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  requestPasswordReset(email: string): Promise<{ message: string }> {
    return publicRequest<{ message: string }>("/auth/password-reset", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },

  confirmPasswordReset(token: string, password: string): Promise<void> {
    return publicRequest<void>(`/auth/password-reset/${encodeURIComponent(token)}`, {
      method: "POST",
      body: JSON.stringify({ password }),
    });
  },
};
