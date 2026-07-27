import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.document import Document
    from app.db.models.document_version import DocumentVersion
    from app.db.models.user import User


class ShareLink(Base):
    """A time-limited, revocable link that lets someone **without an account**
    view a single document version.

    This is the app's only unauthenticated read path — every other document
    route goes through get_current_user. The controls that make that safe
    live here rather than in the endpoint: a link is only usable while it
    has not expired and has not been revoked, and the token itself is never
    stored in a readable form.
    """

    __tablename__ = "share_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # SHA-256 of the token that was handed to the user, never the token
    # itself — same reasoning as password hashing. Anyone who reads this
    # table (a leaked backup, an over-broad query) still cannot open a
    # link. The raw token exists exactly once, in the response that created
    # it, and is unrecoverable afterwards.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Pinned deliberately: the recipient keeps seeing exactly the version
    # that was shared with them, so a later internal upload can never
    # silently change what an external party is looking at.
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Set instead of deleting the row, so a revoked link stays visible in
    # the owner's list (and in any audit) rather than vanishing.
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Minimal usage signal for the owner ("has my client opened this yet?").
    # Deliberately not per-viewer tracking — that would mean logging IPs of
    # people who never agreed to anything, for a feature that doesn't need it.
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped["Document"] = relationship()
    document_version: Mapped["DocumentVersion"] = relationship()
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
