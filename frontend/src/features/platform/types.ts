export interface PlatformAdminSummary {
  id: string;
  displayName: string;
  email: string;
}

export interface PlatformLoginRequest {
  email: string;
  password: string;
}

export interface OrganizationSettings {
  aiSuggestionsEnabled: boolean;
  duplicateDetectionEnabled: boolean;
  /** Total bytes on disk allowed for the organization, not a per-file cap. */
  storageLimitMb: number;
}

export interface OrganizationStats {
  id: string;
  name: string;
  slug: string;
  createdAt: string;
  userCount: number;
  activeUserCount: number;
  documentCount: number;
  settings: OrganizationSettings;
  /**
   * Every version's bytes, including superseded versions and documents in
   * Trash — those files are still on disk, and only a permanent delete
   * removes them. This is the figure storageLimitMb is measured against, and
   * it can be substantially higher than the sizes a user sees in the app
   * (measured on live data: 29.5 MB visible vs 47.9 MB stored). Bytes rather
   * than MB so formatFileSize() can render it.
   */
  storageUsedBytes: number;
}

export interface OrganizationCreateRequest {
  name: string;
}

export interface OrganizationCreated {
  id: string;
  name: string;
  slug: string;
  createdAt: string;
}

export interface FirstAdminCreateRequest {
  email: string;
  displayName: string;
  password: string;
}

export interface FirstAdminCreated {
  id: string;
  email: string;
  displayName: string;
}
