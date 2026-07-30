import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.base import CamelModel


class PlatformAdminSummary(CamelModel):
    id: uuid.UUID
    display_name: str
    email: str


class PlatformLoginRequest(CamelModel):
    email: EmailStr
    password: str = Field(min_length=1)


class PlatformTokenResponse(CamelModel):
    token: str
    expires_at: datetime
    admin: PlatformAdminSummary


class OrganizationSettings(CamelModel):
    """The three per-organization settings, nested rather than flattened onto
    OrganizationStats so the same shape can be reused by the PATCH endpoint in
    Phase 2 without the response and request drifting apart."""

    ai_suggestions_enabled: bool
    duplicate_detection_enabled: bool
    storage_limit_mb: int


class OrganizationStats(CamelModel):
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    user_count: int
    active_user_count: int
    document_count: int
    settings: OrganizationSettings
    # Every version's bytes, Trash and superseded versions included — the
    # figure the storage limit is actually measured against. Bytes rather than
    # MB so the frontend can format it with the existing formatFileSize().
    storage_used_bytes: int


class OrganizationCreate(CamelModel):
    name: str = Field(min_length=1, max_length=200)


class OrganizationCreated(CamelModel):
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime


class FirstAdminCreate(CamelModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=200)
    password: str


class FirstAdminCreated(CamelModel):
    id: uuid.UUID
    email: str
    display_name: str
