import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.db.models import ShareLink, User
from app.db.session import get_db_session
from app.modules.documents.repository import DocumentRepository
from app.modules.shares.repository import ShareLinkRepository
from app.modules.shares.service import ShareService
from app.schemas.share import ShareLinkCreate, ShareLinkCreated, ShareLinkSummary
from app.storage.factory import get_storage

# Owner-facing only. The public, unauthenticated half deliberately lives in a
# separate module (public_router.py) on a different path prefix, so no route
# here can ever be reached without a session by accident.
router = APIRouter(prefix="/api/v1/documents/{document_id}/shares", tags=["shares"])


def get_share_service(db: Session = Depends(get_db_session)) -> ShareService:
    return ShareService(ShareLinkRepository(db), DocumentRepository(db), get_storage())


def _is_active(link: ShareLink) -> bool:
    return link.revoked_at is None and link.expires_at > datetime.now(timezone.utc)


def _to_summary(link: ShareLink) -> ShareLinkSummary:
    return ShareLinkSummary(
        id=link.id,
        version_number=link.document_version.version_number,
        expires_at=link.expires_at,
        revoked_at=link.revoked_at,
        created_at=link.created_at,
        view_count=link.view_count,
        last_viewed_at=link.last_viewed_at,
        is_active=_is_active(link),
    )


@router.post("", response_model=ShareLinkCreated, status_code=201)
def create_share_link(
    document_id: uuid.UUID,
    payload: ShareLinkCreate,
    service: ShareService = Depends(get_share_service),
    current_user: User = Depends(get_current_user),
) -> ShareLinkCreated:
    link, token = service.create_link(
        document_id, expires_in_days=payload.expires_in_days, current_user=current_user
    )
    base = get_settings().public_app_url.rstrip("/")
    return ShareLinkCreated(
        **_to_summary(link).model_dump(),
        token=token,
        url=f"{base}/share/{token}",
    )


@router.get("", response_model=list[ShareLinkSummary])
def list_share_links(
    document_id: uuid.UUID,
    service: ShareService = Depends(get_share_service),
    current_user: User = Depends(get_current_user),
) -> list[ShareLinkSummary]:
    return [_to_summary(link) for link in service.list_links(document_id, current_user=current_user)]


@router.delete("/{link_id}", response_model=ShareLinkSummary)
def revoke_share_link(
    document_id: uuid.UUID,
    link_id: uuid.UUID,
    service: ShareService = Depends(get_share_service),
    current_user: User = Depends(get_current_user),
) -> ShareLinkSummary:
    return _to_summary(service.revoke_link(document_id, link_id, current_user=current_user))
