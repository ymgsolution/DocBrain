import uuid
from datetime import date, datetime

from pydantic import Field

from app.db.models.enums import DocumentStatus
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


class DocumentDetail(DocumentSummary):
    tags: list[TagSummary]
    last_reviewed_at: datetime | None
    last_accessed_at: datetime | None
    status: DocumentStatus


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
