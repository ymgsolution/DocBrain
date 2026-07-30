import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import CamelModel
from app.modules.shares.service import DEFAULT_EXPIRY_DAYS, MAX_EXPIRY_DAYS


class ShareLinkCreate(CamelModel):
    expires_in_days: int = Field(default=DEFAULT_EXPIRY_DAYS, ge=1, le=MAX_EXPIRY_DAYS)
    # An exact moment, for "expires Friday at 5pm" rather than a whole number
    # of days. Optional and takes precedence when set; the preset path is
    # untouched when it isn't. Bounds are enforced in the service, not here,
    # so both routes are checked against the same ceiling in one place.
    expires_at: datetime | None = None


class ShareLinkSummary(CamelModel):
    """What the *owner* sees about their own links. Note there is no token
    field: the raw token is unrecoverable after creation, so this can never
    hand it back. Losing a link means revoking it and issuing a new one."""

    id: uuid.UUID
    version_number: int
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    view_count: int
    last_viewed_at: datetime | None
    is_active: bool


class ShareLinkCreated(ShareLinkSummary):
    """Returned only from the create call — the one and only time the raw
    token is visible. `url` is the complete link, ready to copy."""

    token: str
    url: str


class PublicSharedDocument(CamelModel):
    """The public view. Deliberately minimal: no owner, no category, no
    tags, no review state, no document id, no version history — a recipient
    gets what they need to read the file they were sent, and nothing that
    describes how the organisation works internally."""

    title: str
    original_filename: str
    mime_type: str
    size_bytes: int
    version_number: int
    expires_at: datetime
