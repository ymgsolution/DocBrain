import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.service import DashboardService
from app.schemas.dashboard import ActivityEventOut, CategoryCount, DashboardSummary, DashboardTotals, PagedActivity
from app.schemas.mappers import to_document_summary

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def get_dashboard_service(db: Session = Depends(get_db_session)) -> DashboardService:
    return DashboardService(DashboardRepository(db))


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    service: DashboardService = Depends(get_dashboard_service),
    current_user: User = Depends(get_current_user),
) -> DashboardSummary:
    totals, by_category, recently_added, recently_accessed, expiring_soon, pending_reviews_count = (
        service.get_summary()
    )
    return DashboardSummary(
        totals=DashboardTotals(**totals),
        by_category=[
            CategoryCount(category_id=c.id, category_name=c.name, document_count=n) for c, n in by_category
        ],
        recently_added=[to_document_summary(d) for d in recently_added],
        recently_accessed=[to_document_summary(d) for d in recently_accessed],
        expiring_soon=[to_document_summary(d) for d in expiring_soon],
        pending_reviews_count=pending_reviews_count,
    )


@router.get("/activity", response_model=PagedActivity)
def get_activity(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=25, ge=1, le=100),
    document_id: uuid.UUID | None = Query(default=None, alias="documentId"),
    service: DashboardService = Depends(get_dashboard_service),
    current_user: User = Depends(get_current_user),
) -> PagedActivity:
    items, total = service.list_activity(page, size, document_id=document_id)
    out_items = [
        ActivityEventOut(
            id=e.id,
            document_id=e.document_id,
            document_title=e.document.title if e.document else None,
            actor_name=e.actor.display_name,
            event_type=e.event_type.value,
            summary=e.summary,
            occurred_at=e.occurred_at,
        )
        for e in items
    ]
    return PagedActivity(
        items=out_items,
        page=page,
        size=size,
        total=total,
        total_pages=(total + size - 1) // size if size else 0,
    )
