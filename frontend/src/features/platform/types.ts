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

/**
 * The storage total split into what it's actually made of. Shown as a
 * breakdown rather than one number because the total reads as wrong
 * otherwise: the app displays current versions of active documents, but the
 * limit counts every byte on disk. Measured live, that gap is 38% for the
 * largest organization. The three parts always sum to totalBytes.
 */
export interface StorageBreakdown {
  /** Current versions of active documents — what a user sees in the app. */
  activeCurrentBytes: number;
  /** Older versions kept by the append-only version history. */
  supersededBytes: number;
  /** Documents in Trash. Still on disk until a permanent delete. */
  trashedBytes: number;
  totalBytes: number;
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
  storage: StorageBreakdown;
}

/** Every field optional — omitting one leaves it unchanged. */
export interface OrganizationSettingsUpdateRequest {
  aiSuggestionsEnabled?: boolean;
  duplicateDetectionEnabled?: boolean;
  storageLimitMb?: number;
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
