// Either a preset number of days, or an exact moment (ISO, UTC). The API
// prefers expiresAt when both are present.
export interface ShareLinkCreatePayload {
  expiresInDays?: number;
  expiresAt?: string;
}

export interface ShareLinkSummary {
  id: string;
  versionNumber: number;
  expiresAt: string;
  revokedAt: string | null;
  createdAt: string;
  viewCount: number;
  lastViewedAt: string | null;
  isActive: boolean;
}

// Only ever returned by the create call — the raw token is unrecoverable
// afterwards, so this is the single moment the URL can be shown or copied.
export interface ShareLinkCreated extends ShareLinkSummary {
  token: string;
  url: string;
}

// What a recipient with the link is allowed to see. Deliberately carries no
// owner, category, tags or document id.
export interface PublicSharedDocument {
  title: string;
  originalFilename: string;
  mimeType: string;
  sizeBytes: number;
  versionNumber: number;
  expiresAt: string;
}
