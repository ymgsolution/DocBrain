import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import require_role
from app.db.models import Invitation, User
from app.db.models.enums import UserRole
from app.db.session import get_db_session
from app.modules.auth.repository import AuthRepository
from app.modules.invitations.repository import InvitationRepository
from app.modules.invitations.service import InvitationService
from app.schemas.auth import UserSummary
from app.schemas.invitation import InvitationCreate, InvitationCreated, InvitationSummary

# Admin-only. Inviting someone is granting access to the whole workspace,
# so it sits behind the strictest role rather than the owner/reviewer rule
# used for document actions. The *accept* half is a separate public router.
router = APIRouter(prefix="/api/v1/invitations", tags=["invitations"])


def get_invitation_service(db: Session = Depends(get_db_session)) -> InvitationService:
    return InvitationService(InvitationRepository(db), AuthRepository(db))


def _status(invitation: Invitation) -> str:
    if invitation.accepted_at is not None:
        return "accepted"
    if invitation.revoked_at is not None:
        return "revoked"
    if invitation.expires_at <= datetime.now(timezone.utc):
        return "expired"
    return "pending"


def _to_summary(invitation: Invitation) -> InvitationSummary:
    return InvitationSummary(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        status=_status(invitation),
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        accepted_at=invitation.accepted_at,
        invited_by=UserSummary.model_validate(invitation.inviter, from_attributes=True),
    )


@router.post("", response_model=InvitationCreated, status_code=201)
def create_invitation(
    payload: InvitationCreate,
    service: InvitationService = Depends(get_invitation_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> InvitationCreated:
    invitation, token = service.create(
        email=payload.email,
        role=payload.role,
        expires_in_days=payload.expires_in_days,
        invited_by=current_user,
    )
    base = get_settings().public_app_url.rstrip("/")
    return InvitationCreated(
        **_to_summary(invitation).model_dump(),
        token=token,
        # Returned so the admin can copy it directly. Email delivery is a
        # convenience on top of this, never a prerequisite — an unverified
        # sending domain or a provider outage must not block onboarding.
        url=f"{base}/invite/{token}",
    )


@router.get("", response_model=list[InvitationSummary])
def list_invitations(
    service: InvitationService = Depends(get_invitation_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> list[InvitationSummary]:
    return [_to_summary(i) for i in service.list_all()]


@router.delete("/{invitation_id}", response_model=InvitationSummary)
def revoke_invitation(
    invitation_id: uuid.UUID,
    service: InvitationService = Depends(get_invitation_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> InvitationSummary:
    return _to_summary(service.revoke(invitation_id))
