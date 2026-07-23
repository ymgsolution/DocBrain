import uuid
from datetime import datetime

from app.schemas.auth import UserSummary
from app.schemas.base import CamelModel
from app.schemas.document import CategorySummary


class TrashedDocumentItem(CamelModel):
    id: uuid.UUID
    title: str
    category: CategorySummary
    owner: UserSummary
    deleted_at: datetime
    deleted_by: UserSummary | None


class PagedTrash(CamelModel):
    items: list[TrashedDocumentItem]
    page: int
    size: int
    total: int
    total_pages: int
