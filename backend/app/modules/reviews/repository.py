import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Document
from app.db.models.enums import DocumentStatus


class ReviewsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_pending(
        self,
        *,
        organization_id: uuid.UUID,
        category_id: uuid.UUID | None,
        owner_id: uuid.UUID | None,
        horizon_days: int,
        page: int,
        size: int,
    ) -> tuple[list[Document], int]:
        stmt = (
            select(Document)
            .options(selectinload(Document.category), selectinload(Document.owner))
            .where(
                Document.status == DocumentStatus.ACTIVE,
                Document.review_due_date.is_not(None),
                Document.review_due_date <= func.current_date() + horizon_days,
                Document.organization_id == organization_id,
            )
            .order_by(Document.review_due_date.asc())
        )
        if category_id:
            stmt = stmt.where(Document.category_id == category_id)
        if owner_id:
            stmt = stmt.where(Document.owner_id == owner_id)

        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(Document.id).order_by(None).subquery()
        )
        total = self.db.scalar(count_stmt) or 0

        stmt = stmt.offset(page * size).limit(size)
        items = list(self.db.scalars(stmt))
        return items, total
