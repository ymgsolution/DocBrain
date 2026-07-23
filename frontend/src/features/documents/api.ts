import { apiClient, ApiError, BFF_BASE } from "@/lib/api-client";
import type { ApiErrorBody } from "@/types/api";
import type { DocumentDetail, VersionDetail } from "@/types/document";
import type { DocumentCreatePayload, DocumentListFilters, DocumentUpdatePayload, PagedDocuments } from "./types";

export const documentsApi = {
  list(filters: DocumentListFilters): Promise<PagedDocuments> {
    return apiClient.get<PagedDocuments>("/documents", { ...filters });
  },

  get(id: string): Promise<DocumentDetail> {
    return apiClient.get<DocumentDetail>(`/documents/${id}`);
  },

  update(id: string, payload: DocumentUpdatePayload): Promise<DocumentDetail> {
    return apiClient.patch<DocumentDetail>(`/documents/${id}`, payload);
  },

  softDelete(id: string): Promise<void> {
    return apiClient.delete<void>(`/documents/${id}`);
  },

  restore(id: string): Promise<DocumentDetail> {
    return apiClient.post<DocumentDetail>(`/documents/${id}/restore`);
  },

  hardDelete(id: string): Promise<void> {
    return apiClient.delete<void>(`/documents/${id}/permanent`);
  },

  markReviewed(id: string, note?: string): Promise<DocumentDetail> {
    return apiClient.post<DocumentDetail>(`/documents/${id}/reviews`, { note });
  },

  listVersions(id: string): Promise<VersionDetail[]> {
    return apiClient.get<VersionDetail[]>(`/documents/${id}/versions`);
  },

  restoreVersion(id: string, versionNumber: number): Promise<VersionDetail> {
    return apiClient.post<VersionDetail>(`/documents/${id}/versions/${versionNumber}/restore`, {});
  },

  // XMLHttpRequest instead of fetch — fetch has no cross-browser way to
  // observe upload progress, and the architecture doc requires a
  // determinate progress bar with byte count during upload.
  create(payload: DocumentCreatePayload, onProgress: (percent: number) => void): Promise<DocumentDetail> {
    const formData = new FormData();
    formData.set("file", payload.file);
    formData.set("title", payload.title);
    formData.set("categoryId", payload.categoryId);
    if (payload.description) formData.set("description", payload.description);
    formData.set("tags", payload.tags.join(","));
    if (payload.reviewDueDate) formData.set("reviewDueDate", payload.reviewDueDate);

    return xhrUpload(`${BFF_BASE}/documents`, formData, onProgress);
  },

  uploadVersion(id: string, file: File, changeNote: string, onProgress: (percent: number) => void): Promise<VersionDetail> {
    const formData = new FormData();
    formData.set("file", file);
    formData.set("changeNote", changeNote);

    return xhrUpload(`${BFF_BASE}/documents/${id}/versions`, formData, onProgress);
  },
};

function xhrUpload<T>(url: string, formData: FormData, onProgress: (percent: number) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };

    xhr.onload = () => {
      let data: unknown;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        data = null;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data as T);
      } else {
        reject(new ApiError(xhr.status, data as ApiErrorBody));
      }
    };

    xhr.onerror = () => reject(new Error("Upload failed — nothing was saved, retry?"));

    xhr.send(formData);
  });
}
