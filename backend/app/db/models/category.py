import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # NOT NULL as of the Phase 4 migration (8ebd25762f70) — every write path
    # supplies it (docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md).
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Uniqueness is case-insensitive and scoped per organization — see
    # __table_args__ below.
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_review_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Both of these are per-organization, not global: two organizations may
    # each have their own "General" category, and the default set seeded by
    # OrganizationsService.create_organization relies on exactly that. The
    # global versions these replaced (categories_slug_key,
    # ux_categories_name_lower) were dropped by the Phase 4 migration
    # 8ebd25762f70; they are declared here so `alembic revision
    # --autogenerate` sees the real schema and doesn't try to restore the
    # global ones.
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_categories_organization_id_slug"),
        Index(
            "ux_categories_organization_id_name_lower",
            "organization_id",
            text("lower(name::text)"),
            unique=True,
        ),
    )
