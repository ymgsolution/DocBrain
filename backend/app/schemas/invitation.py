import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.db.models.enums import UserRole
from app.modules.invitations.service import DEFAULT_EXPIRY_DAYS, MAX_EXPIRY_DAYS
from app.schemas.auth import UserSummary
from app.schemas.base import CamelModel


class InvitationCreate(CamelModel):
    email: EmailStr
    role: UserRole = UserRole.EMPLOYEE
    expires_in_days: int = Field(default=DEFAULT_EXPIRY_DAYS, ge=1, le=MAX_EXPIRY_DAYS)


class InvitationSummary(CamelModel):
    """The admin's view. No token field — like share links, the raw token is
    unrecoverable after creation, so a lost invite means revoking and
    sending a new one."""

    id: uuid.UUID
    email: str
    role: UserRole
    status: str  # pending | accepted | revoked | expired
    expires_at: datetime
    created_at: datetime
    accepted_at: datetime | None
    invited_by: UserSummary


class InvitationCreated(InvitationSummary):
    """Returned only from the create call — the one moment the link exists."""

    token: str
    url: str


class PublicInvitation(CamelModel):
    """What the accept page may show *before* anyone proves anything. The
    email is included because the person opening the link needs to see which
    address they're claiming; nothing else about the workspace is exposed."""

    email: str
    role: UserRole
    expires_at: datetime


class InvitationAccept(CamelModel):
    display_name: str = Field(min_length=2, max_length=100)
    # Length is enforced again in the service — this is the friendly,
    # field-level version for the form.
    password: str = Field(min_length=8, max_length=200)
