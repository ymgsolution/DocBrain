import uuid
from datetime import datetime

from app.schemas.base import CamelModel
from app.schemas.document import DocumentSummary


class DashboardTotals(CamelModel):
    total_documents: int
    uploaded_this_week: int
    versions_tracked: int
    categories_in_use: int


class CategoryCount(CamelModel):
    category_id: uuid.UUID
    category_name: str
    document_count: int


class DashboardSummary(CamelModel):
    totals: DashboardTotals
    by_category: list[CategoryCount]
    recently_added: list[DocumentSummary]
    recently_accessed: list[DocumentSummary]
    expiring_soon: list[DocumentSummary]
    pending_reviews_count: int


class ActivityEventOut(CamelModel):
    id: uuid.UUID
    document_id: uuid.UUID | None
    document_title: str | None
    actor_name: str
    event_type: str
    summary: str
    occurred_at: datetime


class PagedActivity(CamelModel):
    items: list[ActivityEventOut]
    page: int
    size: int
    total: int
    total_pages: int
