import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import AiJobStatus, AiJobType

if TYPE_CHECKING:
    from app.db.models.document_version import DocumentVersion


class AiJob(Base):
    """Shared background-work queue for every AI-adjacent processing stage
    (text extraction today; embedding/metadata-suggestion jobs later reuse
    this same table with a different job_type — see the worker's handler
    registry). Claimed via `SELECT ... FOR UPDATE SKIP LOCKED`, the same
    row-locking pattern already used for version-number allocation."""

    __tablename__ = "ai_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[AiJobType] = mapped_column(
        Enum(AiJobType, name="ai_job_type", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[AiJobStatus] = mapped_column(
        Enum(AiJobStatus, name="ai_job_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=AiJobStatus.PENDING,
        server_default=AiJobStatus.PENDING.value,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # NULL = eligible immediately; set on failure to schedule a backoff retry.
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document_version: Mapped["DocumentVersion"] = relationship()

    __table_args__ = (
        # The worker's claim query filters on exactly these two columns.
        Index("ix_ai_jobs_status_next_retry_at", "status", "next_retry_at"),
    )
