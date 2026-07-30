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


class OrganizationSettingsUpdate(CamelModel):
    """Every field optional — a PATCH that changes one toggle shouldn't have
    to restate the other two, and omitting a field is how the caller says
    "leave this alone". None therefore means untouched, never "set to null".
    """

    ai_suggestions_enabled: bool | None = None
    duplicate_detection_enabled: bool | None = None
    # Bounded on both ends: 0 would lock an organization out of uploading
    # entirely with no way back except another PATCH, and an unbounded upper
    # value makes the limit meaningless. 1 TB is far above anything this
    # deployment will see and still rejects a fat-fingered extra digit.
    storage_limit_mb: int | None = Field(default=None, ge=1, le=1_000_000)


class StorageBreakdown(CamelModel):
    """The storage total split into the three things it's actually made of.

    A single number reads as wrong to whoever is looking at it: the app shows
    the current versions of active documents, but the limit counts every byte
    on disk. Measured live, that gap is 38% for the original organization
    (29.5 MB visible vs 47.9 MB stored). These three partition every version
    exactly once, so they always sum to `total_bytes`.
    """

    # Current versions of active documents — what a user sees in the app.
    active_current_bytes: int
    # Older versions kept by the append-only version history.
    superseded_bytes: int
    # Everything belonging to documents sitting in Trash. Still on disk:
    # soft delete only flips a status, and only a permanent delete (which is
    # admin-only) actually frees the space.
    trashed_bytes: int
    total_bytes: int


class OrganizationStats(CamelModel):
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    user_count: int
    active_user_count: int
    document_count: int
    settings: OrganizationSettings
    # Bytes rather than MB so the frontend can format with the existing
    # formatFileSize(); `storage.total_bytes` is the figure the limit is
    # measured against.
    storage: StorageBreakdown


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
