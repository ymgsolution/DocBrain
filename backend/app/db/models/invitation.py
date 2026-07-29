import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import UserRole

if TYPE_CHECKING:
    from app.db.models.user import User


class Invitation(Base):
    """An admin's offer of an account. Signup is invite-only, so this is the
    only way a new user comes into existence.

    Same token discipline as ShareLink: a long random value, stored only as
    a hash, single-use and time-limited. The difference is what accepting it
    does — a share link grants a peek at one document, this one creates a
    real account with a role.
    """

    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Who the invitee is joining — the inviting admin's own organization.
    # Nullable for now — see the Phase 2 migration
    # (docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md) for why NOT NULL isn't set
    # until every write path supplies it.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    # SHA-256 of the token in the invite URL, never the token itself — a
    # leaked backup shouldn't hand someone an account.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # Stored lowercased. Not a FK to users: the whole point is that this
    # person has no account yet. The uniqueness that matters (one account
    # per address) is enforced on users.email at accept time.
    email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # Chosen by the admin when inviting, so a new joiner lands with the right
    # permissions instead of everyone starting as an employee and being
    # promoted afterwards.
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Set once, on acceptance — this is what makes an invite single-use. A
    # timestamp rather than a boolean so the admin list can show *when*
    # someone joined without a second column.
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    invited_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # The account this invite produced, once accepted. Nullable until then.
    accepted_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    inviter: Mapped["User"] = relationship(foreign_keys=[invited_by])
    accepted_user: Mapped["User | None"] = relationship(foreign_keys=[accepted_user_id])
