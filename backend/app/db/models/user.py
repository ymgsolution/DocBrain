import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import UserRole

if TYPE_CHECKING:
    from app.db.models.organization import Organization
    from app.db.models.user_preference import UserPreference


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Nullable for now, matching the DB column added in the Phase 2 migration
    # (docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md) — every existing row is
    # already backfilled, but NOT NULL is only added once every write path
    # (invitation accept, seed scripts) reliably supplies it (Phase 4).
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    # Nullable on purpose: an invited user exists (so their role and any
    # assigned documents are real) before they've ever set a password. Until
    # they accept the invite this stays NULL and verify_password rejects
    # every attempt, so a pending invite can't be logged into.
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    # Never delete a user to revoke access — documents.owner_id is ON DELETE
    # RESTRICT, so Postgres refuses outright once they own anything, and
    # activity_events/document_versions would lose the author of real history.
    # Flipping this instead is both permitted and reversible, and it bites
    # immediately: get_current_user re-reads this row on every request, so a
    # still-valid token stops working on the next click.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    organization: Mapped["Organization | None"] = relationship(foreign_keys=[organization_id], lazy="joined")
    preferences: Mapped["UserPreference | None"] = relationship(back_populates="user", uselist=False)
    # Self-referential, so remote_side/foreign_keys have to be spelled out —
    # without them SQLAlchemy can't tell which end of a users->users FK this
    # side of the relationship sits on. Read-only in practice: the service
    # writes the deactivated_by column, never this.
    deactivator: Mapped["User | None"] = relationship(
        "User", remote_side=[id], foreign_keys=[deactivated_by], lazy="joined"
    )
