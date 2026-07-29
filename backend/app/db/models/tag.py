import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # NOT NULL as of the Phase 4 migration (8ebd25762f70) — every write path
    # supplies it (docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md).
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String, nullable=False)
    # Maintained by a trigger on document_tags insert/delete — see migration.
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # Per-organization, not global: each organization owns its own tag
    # vocabulary, so "urgent" in one org is a different row from "urgent" in
    # another. Replaced the global tags_normalized_name_key in the Phase 4
    # migration 8ebd25762f70; declared here so `alembic revision
    # --autogenerate` doesn't try to restore the global one.
    __table_args__ = (
        UniqueConstraint("organization_id", "normalized_name", name="uq_tags_organization_id_normalized_name"),
    )


class DocumentTag(Base):
    __tablename__ = "document_tags"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
