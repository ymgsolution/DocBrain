import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.db.models.enums import ThemePreference, UserRole
from app.schemas.base import CamelModel


class OrganizationSummary(CamelModel):
    id: uuid.UUID
    name: str
    slug: str


class UserSummary(CamelModel):
    id: uuid.UUID
    display_name: str
    email: str
    role: UserRole
    # Nullable until Phase 4 makes organization_id required on every user —
    # see docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md.
    organization: OrganizationSummary | None = None


class LoginRequest(CamelModel):
    email: EmailStr
    # No max/complexity rules on *login* deliberately — those belong on the
    # set-password path. Rejecting a login for a "too short" password just
    # leaks that the stored one doesn't look like that.
    password: str = Field(min_length=1)


class PasswordResetRequest(CamelModel):
    email: EmailStr


class PasswordResetConfirm(CamelModel):
    password: str = Field(min_length=8, max_length=200)


class TokenResponse(CamelModel):
    token: str
    expires_at: datetime
    user: UserSummary


class UserPreferencesOut(CamelModel):
    theme: ThemePreference
    default_page_size: int


class UserPreferencesUpdate(CamelModel):
    theme: ThemePreference | None = None
    default_page_size: int | None = Field(default=None, ge=1, le=100)
