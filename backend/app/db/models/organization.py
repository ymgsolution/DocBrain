import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Every row that pre-dates multi-tenancy is backfilled onto this one
# organization (see docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md, Part 9). Fixed
# rather than looked up so the migration that creates it and every later
# migration that backfills onto it agree on the same id without a query.
DEFAULT_ORGANIZATION_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_ORGANIZATION_NAME = "Accenture"
DEFAULT_ORGANIZATION_SLUG = "accenture"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
