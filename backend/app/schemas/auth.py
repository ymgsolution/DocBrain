import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.db.models.enums import ThemePreference, UserRole
from app.schemas.base import CamelModel


class UserSummary(CamelModel):
    id: uuid.UUID
    display_name: str
    email: str
    role: UserRole


class LoginRequest(CamelModel):
    email: EmailStr


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
