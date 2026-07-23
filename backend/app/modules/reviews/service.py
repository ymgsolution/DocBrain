import uuid
from datetime import date, datetime, timedelta, timezone

from app.core.exceptions import NotFoundError
from app.db.models import ActivityEvent, Document, User
from app.db.models.enums import ActivityEventType
from app.modules.documents.repository import DocumentRepository
from app.modules.reviews.repository import ReviewsRepository

REVIEW_HORIZON_DAYS = 30


def review_status_and_days_overdue(review_due_date: date, today: date) -> tuple[str, int]:
    if review_due_date < today:
        return "overdue", (today - review_due_date).days
    return "due_soon", 0


class ReviewsService:
    def __init__(self, repository: ReviewsRepository, document_repository: DocumentRepository) -> None:
        self.repository = repository
        self.document_repository = document_repository

    def list_pending(
        self, *, category_id: uuid.UUID | None, owner_id: uuid.UUID | None, page: int, size: int
    ) -> tuple[list[Document], int]:
        return self.repository.list_pending(
            category_id=category_id, owner_id=owner_id, horizon_days=REVIEW_HORIZON_DAYS, page=page, size=size
        )

    def mark_reviewed(self, document_id: uuid.UUID, *, note: str | None, current_user: User) -> Document:
        document = self.document_repository.get_active_by_id(document_id)
        if document is None:
            raise NotFoundError("This document doesn't exist or was deleted.")

        now = datetime.now(timezone.utc)
        document.last_reviewed_at = now
        document.last_reviewed_by = current_user.id

        period_days = document.category.default_review_period_days
        if period_days:
            document.review_due_date = (now + timedelta(days=period_days)).date()
        # else: category has no default review period — leave the due date as-is;
        # a reviewer/admin can set a new one explicitly via PATCH if needed.

        summary = f"{current_user.display_name} marked “{document.title}” as reviewed"
        if note:
            summary += f" — {note}"

        self.document_repository.db.add(
            ActivityEvent(
                document_id=document.id,
                actor_id=current_user.id,
                event_type=ActivityEventType.REVIEWED,
                summary=summary,
            )
        )
        self.document_repository.db.commit()
        self.document_repository.db.refresh(document)
        return document
