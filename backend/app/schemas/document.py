import uuid
from datetime import date, datetime

from pydantic import Field

from app.db.models.enums import DocumentStatus, ExtractionStatus
from app.schemas.auth import UserSummary
from app.schemas.base import CamelModel
from app.schemas.version import VersionSummary


class CategorySummary(CamelModel):
    id: uuid.UUID
    name: str
    slug: str


class TagSummary(CamelModel):
    id: uuid.UUID
    name: str


class DocumentSummary(CamelModel):
    id: uuid.UUID
    title: str
    description: str | None
    category: CategorySummary
    owner: UserSummary
    current_version: VersionSummary | None
    version_count: int
    review_due_date: date | None
    updated_at: datetime
    created_at: datetime


class AiSuggestion(CamelModel):
    """Shadow-mode metadata suggestion, only surfaced once SUCCEEDED — a
    PENDING/FAILED/SKIPPED analysis row (or none at all) simply means no
    suggestion, not an error."""

    title: str | None = None
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)


class DocumentDetail(DocumentSummary):
    tags: list[TagSummary]
    last_reviewed_at: datetime | None
    last_accessed_at: datetime | None
    status: DocumentStatus
    # AI feature track — null means no document_extracted_text row exists yet
    # (the AiJob hasn't been claimed by the worker), which the frontend
    # treats identically to PENDING: still show the "Analyzing…" badge.
    extraction_status: ExtractionStatus | None = None
    # AI feature track (Phase 2) — null whenever there's nothing to show yet
    # (no job run, still pending, or it failed); the UI simply omits the card.
    ai_suggestion: AiSuggestion | None = None


class DocumentCreateMetadata(CamelModel):
    title: str = Field(min_length=3, max_length=200)
    category_id: uuid.UUID
    description: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list, max_length=10)
    review_due_date: date | None = None


class DocumentUpdate(CamelModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    category_id: uuid.UUID | None = None
    tags: list[str] | None = Field(default=None, max_length=10)
    review_due_date: date | None = None
    owner_id: uuid.UUID | None = None


class PagedDocuments(CamelModel):
    items: list[DocumentSummary]
    page: int
    size: int
    total: int
    total_pages: int
