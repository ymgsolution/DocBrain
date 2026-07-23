import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import ExtractionMethod, ExtractionStatus

if TYPE_CHECKING:
    from app.db.models.document_version import DocumentVersion


class DocumentExtractedText(Base):
    """Metadata + a pointer to the extracted-text file on disk — never the
    text content itself. The content lives at `extracted_text_path`
    (`{version.storage_path}.txt`, via StoragePort), the same split
    DocumentVersion already uses for its own file."""

    __tablename__ = "document_extracted_text"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    extracted_text_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_method: Mapped[ExtractionMethod | None] = mapped_column(
        Enum(ExtractionMethod, name="extraction_method", values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus, name="extraction_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=ExtractionStatus.PENDING,
        server_default=ExtractionStatus.PENDING.value,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document_version: Mapped["DocumentVersion"] = relationship()
