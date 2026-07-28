import { apiClient } from "@/lib/api-client";
import type { InvitationCreated, InvitationSummary } from "@/types/invitation";
import type { UserRole } from "@/types/api";

export const invitationsApi = {
  list(): Promise<InvitationSummary[]> {
    return apiClient.get<InvitationSummary[]>("/invitations");
  },

  create(payload: { email: string; role: UserRole; expiresInDays: number }): Promise<InvitationCreated> {
    return apiClient.post<InvitationCreated>("/invitations", payload);
  },

  revoke(id: string): Promise<InvitationSummary> {
    return apiClient.delete<InvitationSummary>(`/invitations/${id}`);
  },
};
