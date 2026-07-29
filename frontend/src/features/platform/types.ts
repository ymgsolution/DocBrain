export interface PlatformAdminSummary {
  id: string;
  displayName: string;
  email: string;
}

export interface PlatformLoginRequest {
  email: string;
  password: string;
}

export interface OrganizationStats {
  id: string;
  name: string;
  slug: string;
  createdAt: string;
  userCount: number;
  activeUserCount: number;
  documentCount: number;
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
