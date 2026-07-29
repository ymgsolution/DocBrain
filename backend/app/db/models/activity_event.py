import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import ActivityEventType

if TYPE_CHECKING:
    from app.db.models.document import Document
    from app.db.models.user import User


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Nullable for now — see the Phase 2 migration
    # (docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md) for why NOT NULL isn't set
    # until every write path supplies it.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_type: Mapped[ActivityEventType] = mapped_column(
        Enum(ActivityEventType, name="activity_event_type", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    document: Mapped["Document | None"] = relationship()
    actor: Mapped["User"] = relationship()
