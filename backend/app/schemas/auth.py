import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.db.models.enums import ThemePreference, UserRole
from app.schemas.base import CamelModel


class OrganizationSummary(CamelModel):
    id: uuid.UUID
    name: str
    slug: str
    # The two AI settings travel with the user rather than getting their own
    # endpoint: User.organization is already eager-loaded (lazy="joined") on
    # every authenticated request, so this costs no extra query, and the app
    # needs them on first paint.
    #
    # Read-only by design. A tenant admin must never be able to change these —
    # every mutation lives under /platform behind get_current_platform_admin.
    # storage_limit_mb is deliberately *not* exposed here: nothing in the
    # tenant app needs it yet, and the upload error carries its own message.
    #
    # The app needs these, not just empty results: "no suggestion yet" and
    # "suggestions are switched off" look identical in the document payload,
    # and the frontend's isAiSuggestionPending() heuristic would otherwise
    # poll every 2s and show "Getting AI suggestions…" for two minutes after
    # every upload on an organization that has them disabled.
    ai_suggestions_enabled: bool
    duplicate_detection_enabled: bool


class UserSummary(CamelModel):
    id: uuid.UUID
    display_name: str
    email: str
    role: UserRole
    # Optional on the wire even though users.organization_id has been NOT NULL
    # since migration 8ebd25762f70: this schema is nested inside version,
    # trash and admin responses whose queries don't all eager-load the
    # relationship, and tightening it would turn a missing join into a 500
    # rather than an absent field. The frontend type mirrors this.
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
