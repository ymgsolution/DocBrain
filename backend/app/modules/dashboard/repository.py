import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ActivityEvent, Category, Document, DocumentVersion
from app.db.models.enums import DocumentStatus


class DashboardRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def total_documents(self) -> int:
        stmt = select(func.count(Document.id)).where(Document.status == DocumentStatus.ACTIVE)
        return self.db.scalar(stmt) or 0

    def uploaded_this_week(self, since: datetime) -> int:
        stmt = select(func.count(Document.id)).where(
            Document.status == DocumentStatus.ACTIVE, Document.created_at >= since
        )
        return self.db.scalar(stmt) or 0

    def versions_tracked(self) -> int:
        return self.db.scalar(select(func.count(DocumentVersion.id))) or 0

    def categories_in_use(self) -> int:
        stmt = select(func.count(func.distinct(Document.category_id))).where(
            Document.status == DocumentStatus.ACTIVE
        )
        return self.db.scalar(stmt) or 0

    def by_category(self) -> list[tuple[Category, int]]:
        stmt = (
            select(Category, func.count(Document.id))
            .join(Document, Document.category_id == Category.id)
            .where(Document.status == DocumentStatus.ACTIVE)
            .group_by(Category.id)
            .order_by(func.count(Document.id).desc())
        )
        return [(row[0], row[1]) for row in self.db.execute(stmt)]

    def _summary_query(self):
        return (
            select(Document)
            .options(
                selectinload(Document.category),
                selectinload(Document.owner),
                selectinload(Document.current_version).selectinload(DocumentVersion.uploader),
            )
            .where(Document.status == DocumentStatus.ACTIVE)
        )

    def recently_added(self, limit: int) -> list[Document]:
        stmt = self._summary_query().order_by(Document.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt))

    def recently_accessed(self, limit: int) -> list[Document]:
        stmt = (
            self._summary_query()
            .where(Document.last_accessed_at.is_not(None))
            .order_by(Document.last_accessed_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def expiring_soon(self, horizon_days: int, limit: int) -> list[Document]:
        stmt = (
            self._summary_query()
            .where(
                Document.review_due_date.is_not(None),
                Document.review_due_date <= func.current_date() + horizon_days,
            )
            .order_by(Document.review_due_date.asc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def pending_reviews_count(self, horizon_days: int) -> int:
        stmt = select(func.count(Document.id)).where(
            Document.status == DocumentStatus.ACTIVE,
            Document.review_due_date.is_not(None),
            Document.review_due_date <= func.current_date() + horizon_days,
        )
        return self.db.scalar(stmt) or 0

    def list_activity(
        self, page: int, size: int, *, document_id: uuid.UUID | None = None
    ) -> tuple[list[ActivityEvent], int]:
        count_stmt = select(func.count(ActivityEvent.id))
        stmt = select(ActivityEvent).options(
            selectinload(ActivityEvent.document), selectinload(ActivityEvent.actor)
        )
        if document_id is not None:
            count_stmt = count_stmt.where(ActivityEvent.document_id == document_id)
            stmt = stmt.where(ActivityEvent.document_id == document_id)

        total = self.db.scalar(count_stmt) or 0
        stmt = stmt.order_by(ActivityEvent.occurred_at.desc()).offset(page * size).limit(size)
        items = list(self.db.scalars(stmt))
        return items, total
