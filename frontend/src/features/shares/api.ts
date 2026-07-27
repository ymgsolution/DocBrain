import { apiClient } from "@/lib/api-client";
import type { ShareLinkCreatePayload, ShareLinkCreated, ShareLinkSummary } from "@/types/share";

export const sharesApi = {
  list(documentId: string): Promise<ShareLinkSummary[]> {
    return apiClient.get<ShareLinkSummary[]>(`/documents/${documentId}/shares`);
  },

  create(documentId: string, payload: ShareLinkCreatePayload): Promise<ShareLinkCreated> {
    return apiClient.post<ShareLinkCreated>(`/documents/${documentId}/shares`, payload);
  },

  revoke(documentId: string, linkId: string): Promise<ShareLinkSummary> {
    return apiClient.delete<ShareLinkSummary>(`/documents/${documentId}/shares/${linkId}`);
  },
};
