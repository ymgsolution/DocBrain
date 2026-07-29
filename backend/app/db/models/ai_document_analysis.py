import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import AiAnalysisStatus

if TYPE_CHECKING:
    from app.db.models.document_version import DocumentVersion
    from app.db.models.user import User


class AiDocumentAnalysis(Base):
    """Named `analysis`, not `metadata`, deliberately: this milestone only
    populates the suggested_*/confidence_score columns (metadata generation),
    but the table is meant to hold whatever future AI outputs land on a
    document_version — summaries, entities, topics, compliance results — as
    additive nullable columns, without renaming the table again. One row per
    document_version for now (see AiJobType.GENERATE_METADATA); a discriminator
    column can be added later if/when a second analysis kind needs its own row
    per version rather than sharing this one.

    raw_response is the provider's raw JSON text, kept alongside the validated
    suggested_* fields so shadow-mode results can be debugged/re-evaluated
    even if the Pydantic schema changes later and reprocessing isn't an option.

    accepted/accepted_by/accepted_at/edited are nullable and unused until the
    review UI exists — they let that UI measure suggestion quality (acceptance
    rate, edit rate) from day one instead of needing another migration then.
    """

    __tablename__ = "ai_document_analysis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # NOT NULL as of the Phase 4 migration (8ebd25762f70). Defense-in-depth:
    # the same "join through document_versions to reach the owning org" shape
    # that let the pre-migration similarity search leak across tenants
    # (docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md).
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

    suggested_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_category: Mapped[str | None] = mapped_column(String, nullable=True)
    suggested_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    suggested_keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_name: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String, nullable=True)
    input_char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Review UI (not built yet) will set these when a reviewer accepts/edits
    # a suggestion — left nullable/unset until then.
    accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edited: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    document_version: Mapped["DocumentVersion"] = relationship(back_populates="analysis")
    accepted_by_user: Mapped["User | None"] = relationship(foreign_keys=[accepted_by])
