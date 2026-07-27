import { apiClient } from "@/lib/api-client";
import type { ShareLinkCreated, ShareLinkSummary } from "@/types/share";

export const sharesApi = {
  list(documentId: string): Promise<ShareLinkSummary[]> {
    return apiClient.get<ShareLinkSummary[]>(`/documents/${documentId}/shares`);
  },

  create(documentId: string, expiresInDays: number): Promise<ShareLinkCreated> {
    return apiClient.post<ShareLinkCreated>(`/documents/${documentId}/shares`, { expiresInDays });
  },

  revoke(documentId: string, linkId: string): Promise<ShareLinkSummary> {
    return apiClient.delete<ShareLinkSummary>(`/documents/${documentId}/shares/${linkId}`);
  },
};
