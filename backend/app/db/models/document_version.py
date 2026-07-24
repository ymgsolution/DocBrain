import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.ai_document_analysis import AiDocumentAnalysis
    from app.db.models.document import Document
    from app.db.models.document_extracted_text import DocumentExtractedText
    from app.db.models.user import User


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    # Mandatory from v2 onward — enforced in the service layer, not the DB,
    # since version 1 legitimately has none.
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # SET NULL, not the default RESTRICT: without it, hard-deleting a document
    # whose versions include a restore (v3.restored_from_version_id -> v1)
    # fails, because the FK still points at v1 while it's being deleted in the
    # same cascade batch. This is provenance metadata, not a required link, so
    # losing it on purge is correct.
    restored_from_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True
    )

    document: Mapped["Document"] = relationship(back_populates="versions", foreign_keys=[document_id])
    uploader: Mapped["User"] = relationship(foreign_keys=[uploaded_by])
    # AI feature track — the extraction-status badge on Document Details
    # reads this via current_version.extracted_text, eager-loaded alongside
    # it rather than a separate query.
    #
    # passive_deletes=True: without it, hard-deleting a document whose
    # current_version.extracted_text was eager-loaded (get_detail's
    # _detail_query()) makes the ORM try to UPDATE document_extracted_text
    # SET document_version_id=NULL when this version is deleted — a 500,
    # since that column is NOT NULL. The DB's own ON DELETE CASCADE (on
    # DocumentExtractedText.document_version_id) already handles this
    # correctly; passive_deletes tells SQLAlchemy to trust it and not try to
    # null the FK itself.
    extracted_text: Mapped["DocumentExtractedText | None"] = relationship(
        back_populates="document_version", uselist=False, passive_deletes=True
    )
    # Same passive_deletes=True reasoning as extracted_text above — this
    # relationship isn't eager-loaded yet, but declaring it up front avoids
    # re-discovering the hard-delete 500 the moment something does eager-load it.
    analysis: Mapped["AiDocumentAnalysis | None"] = relationship(
        back_populates="document_version", uselist=False, passive_deletes=True
    )

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_versions_document_id_version_number"),
    )
