import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Defaults for a new organization, and — via server_default on the migration
# that adds these columns — for every organization that already existed.
DEFAULT_AI_SUGGESTIONS_ENABLED = True
DEFAULT_DUPLICATE_DETECTION_ENABLED = True
DEFAULT_STORAGE_LIMIT_MB = 150

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

    # Organization settings — plain columns rather than a separate
    # organization_settings table, deliberately. A child settings row is
    # something that has to be *created* for every new organization, and this
    # project has already shipped three bugs of exactly that shape (a new
    # organization with no categories, then categories with no review period,
    # then AI rows with no organization_id — see §3 of PROJECT_STATUS.md).
    # NOT NULL columns with a server_default make "an organization without
    # settings" unrepresentable instead of merely unlikely, and mean
    # OrganizationsService.create_organization needs no changes at all.
    #
    # Revisit if these grow past roughly ten, or ever need their own audit
    # history — moving them to a table later is a mechanical migration.
    ai_suggestions_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=DEFAULT_AI_SUGGESTIONS_ENABLED, server_default="true"
    )
    duplicate_detection_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=DEFAULT_DUPLICATE_DETECTION_ENABLED, server_default="true"
    )
    # Total bytes on disk for this organization, not a per-file cap (that's
    # settings.max_upload_size_mb, unchanged). Counts *every* version's
    # size_bytes, including superseded versions and documents sitting in
    # Trash — those bytes are genuinely still stored; only a permanent delete
    # frees them.
    storage_limit_mb: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_STORAGE_LIMIT_MB, server_default=str(DEFAULT_STORAGE_LIMIT_MB)
    )
