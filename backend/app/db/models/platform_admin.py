import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlatformAdmin(Base):
    """Manages organizations, not documents. Deliberately not a User row:
    a platform admin belongs to no organization, so mixing it into the
    `users` table would mean either an exception to `users.organization_id`
    being required (weakening a guarantee every other query relies on) or a
    role value that every existing per-org query has to remember to exclude.
    A separate table means a platform admin token can never be mistaken for
    a User token, and a platform admin can structurally never appear in any
    org-scoped query — there is no column here for one to leak through.

    No role/permission levels for now — a small, trusted internal team, not
    a hierarchy. is_active exists for the same reason users.is_active
    does: revoke a departed or compromised account without deleting the row
    (and losing the audit trail of what organizations they created).
    """

    __tablename__ = "platform_admins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
