import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
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
    # Mandatory, not just defense-in-depth: this is the column the
    # similarity search filters on directly, rather than relying on the
    # document_versions -> documents join chain — that join chain is exactly
    # how the pre-migration version of this query had no tenant isolation at
    # all (docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md, Part 7). NOT NULL as of
    # the Phase 4 migration (8ebd25762f70).
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
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

    # The HNSW index that makes similarity search an approximate-nearest-
    # neighbour lookup instead of a sequential scan over every embedding.
    # Created with raw op.execute() in the migration (pgvector index types
    # aren't expressible via index=True); declared here so `alembic revision
    # --autogenerate` doesn't read it as "removed" and drop it.
    __table_args__ = (
        Index(
            "ix_document_vector_embeddings_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
