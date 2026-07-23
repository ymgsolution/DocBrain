import uuid
from datetime import date

from pydantic import Field

from app.schemas.auth import UserSummary
from app.schemas.base import CamelModel
from app.schemas.document import CategorySummary


class PendingReviewItem(CamelModel):
    id: uuid.UUID
    title: str
    category: CategorySummary
    owner: UserSummary
    review_due_date: date
    review_status: str  # "due_soon" | "overdue"
    days_overdue: int  # 0 while still due-soon; positive once past the due date


class PagedPendingReviews(CamelModel):
    items: list[PendingReviewItem]
    page: int
    size: int
    total: int
    total_pages: int


class MarkReviewedRequest(CamelModel):
    note: str | None = Field(default=None, max_length=1000)
