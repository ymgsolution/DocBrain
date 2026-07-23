import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import DocumentStatus

if TYPE_CHECKING:
    from app.db.models.category import Category
    from app.db.models.document_version import DocumentVersion
    from app.db.models.tag import Tag
    from app.db.models.user import User


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Circular reference with document_versions — resolved with use_alter so the
    # FK is added via ALTER TABLE after both tables exist (see migration).
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "document_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_documents_current_version_id",
        ),
        nullable=True,
    )
    version_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    review_due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=DocumentStatus.ACTIVE,
        server_default=DocumentStatus.ACTIVE.value,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Maintained by a trigger (title/description/category/tags) — see migration.
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), index=True
    )

    category: Mapped["Category"] = relationship()
    owner: Mapped["User"] = relationship(foreign_keys=[owner_id])
    current_version: Mapped["DocumentVersion | None"] = relationship(
        foreign_keys=[current_version_id], post_update=True
    )
    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document",
        foreign_keys="DocumentVersion.document_id",
        cascade="all, delete-orphan",
    )
    # Reads through document_tags; writes go through DocumentTag rows directly
    # (so assigned_at and the tags.usage_count trigger stay correct).
    tags: Mapped[list["Tag"]] = relationship(secondary="document_tags", viewonly=True)
