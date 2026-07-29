import uuid
from datetime import datetime, timedelta, timezone

from app.db.models import ActivityEvent, Category, Document
from app.modules.dashboard.repository import DashboardRepository

REVIEW_HORIZON_DAYS = 30
RECENT_LIMIT = 10


class DashboardService:
    def __init__(self, repository: DashboardRepository) -> None:
        self.repository = repository

    def get_summary(
        self, organization_id: uuid.UUID
    ) -> tuple[dict, list[tuple[Category, int]], list[Document], list[Document], list[Document], int]:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        totals = {
            "total_documents": self.repository.total_documents(organization_id),
            "uploaded_this_week": self.repository.uploaded_this_week(since, organization_id),
            "versions_tracked": self.repository.versions_tracked(organization_id),
            "categories_in_use": self.repository.categories_in_use(organization_id),
        }
        by_category = self.repository.by_category(organization_id)
        recently_added = self.repository.recently_added(RECENT_LIMIT, organization_id)
        recently_accessed = self.repository.recently_accessed(RECENT_LIMIT, organization_id)
        expiring_soon = self.repository.expiring_soon(REVIEW_HORIZON_DAYS, RECENT_LIMIT, organization_id)
        pending_reviews_count = self.repository.pending_reviews_count(REVIEW_HORIZON_DAYS, organization_id)
        return totals, by_category, recently_added, recently_accessed, expiring_soon, pending_reviews_count

    def list_activity(
        self, page: int, size: int, *, organization_id: uuid.UUID, document_id: uuid.UUID | None = None
    ) -> tuple[list[ActivityEvent], int]:
        return self.repository.list_activity(page, size, organization_id=organization_id, document_id=document_id)
