import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.db.models import User
from app.db.models.enums import UserRole
from app.db.session import get_db_session
from app.modules.documents.repository import DocumentRepository
from app.modules.reviews.repository import ReviewsRepository
from app.modules.reviews.service import ReviewsService, review_status_and_days_overdue
from app.schemas.auth import UserSummary
from app.schemas.document import CategorySummary, DocumentDetail
from app.schemas.mappers import to_document_detail
from app.schemas.review import MarkReviewedRequest, PagedPendingReviews, PendingReviewItem

router = APIRouter(prefix="/api/v1", tags=["reviews"])


def get_reviews_service(db: Session = Depends(get_db_session)) -> ReviewsService:
    return ReviewsService(ReviewsRepository(db), DocumentRepository(db))


@router.get("/reviews/pending", response_model=PagedPendingReviews)
def list_pending_reviews(
    category_id: uuid.UUID | None = Query(default=None, alias="categoryId"),
    owner_id: uuid.UUID | None = Query(default=None, alias="ownerId"),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=25, ge=1, le=100),
    service: ReviewsService = Depends(get_reviews_service),
    current_user: User = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN)),
) -> PagedPendingReviews:
    items, total = service.list_pending(
        organization_id=current_user.organization_id,
        category_id=category_id,
        owner_id=owner_id,
        page=page,
        size=size,
    )
    today = datetime.now(timezone.utc).date()

    out_items = []
    for d in items:
        status, days_overdue = review_status_and_days_overdue(d.review_due_date, today)
        out_items.append(
            PendingReviewItem(
                id=d.id,
                title=d.title,
                category=CategorySummary.model_validate(d.category, from_attributes=True),
                owner=UserSummary.model_validate(d.owner, from_attributes=True),
                review_due_date=d.review_due_date,
                review_status=status,
                days_overdue=days_overdue,
            )
        )

    return PagedPendingReviews(
        items=out_items,
        page=page,
        size=size,
        total=total,
        total_pages=(total + size - 1) // size if size else 0,
    )


@router.post("/documents/{document_id}/reviews", response_model=DocumentDetail)
def mark_reviewed(
    document_id: uuid.UUID,
    payload: MarkReviewedRequest,
    service: ReviewsService = Depends(get_reviews_service),
    current_user: User = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN)),
) -> DocumentDetail:
    document = service.mark_reviewed(document_id, note=payload.note, current_user=current_user)
    return to_document_detail(document, ai_suggestions_enabled=current_user.organization.ai_suggestions_enabled)
