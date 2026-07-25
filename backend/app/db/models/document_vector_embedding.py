import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import AiAnalysisStatus

if TYPE_CHECKING:
    from app.db.models.document_version import DocumentVersion


class DocumentVectorEmbedding(Base):
    """Similar Document Detection track. Kept fully separate from
    ai_document_analysis (which holds scalar suggested_*/confidence columns)
    since vectors are a different shape and are queried via pgvector ANN
    search (embedding <=> :query), not simple selects. One row per
    document_version, same 1:1 shape as AiDocumentAnalysis, populated by the
    same async-job/worker pattern (AiJobType.GENERATE_EMBEDDING) — hence the
    identical status/error/retry/latency observability columns.

    embedding is nullable until status=SUCCEEDED. embedding_model/dimension
    are stored per-row (not just read from config) so a future change to
    ai_embedding_dimensions/gemini_embedding_model doesn't silently mix
    vectors from different spaces in the same similarity query — a consumer
    can filter/detect on these columns instead of assuming they're uniform.
    """

    __tablename__ = "document_vector_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[AiAnalysisStatus] = mapped_column(
        Enum(AiAnalysisStatus, name="ai_analysis_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=AiAnalysisStatus.PENDING,
        server_default=AiAnalysisStatus.PENDING.value,
    )

    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String, nullable=True)
    embedding_dimension: Mapped[int | None] = mapped_column(Integer, nullable=True)

    input_char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    document_version: Mapped["DocumentVersion"] = relationship(back_populates="embedding")
