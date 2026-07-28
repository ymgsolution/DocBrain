import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import require_role
from app.email.factory import get_email_sender
from app.email.messages import invitation_email
from app.email.port import EmailError, EmailSender
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
logger = logging.getLogger(__name__)

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
    # Injected rather than called inline so tests can substitute a fake and
    # never touch the network — the same dependency-override seam used for
    # storage and the document services.
    email: EmailSender = Depends(get_email_sender),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> InvitationCreated:
    invitation, token = service.create(
        email=payload.email,
        role=payload.role,
        expires_in_days=payload.expires_in_days,
        invited_by=current_user,
    )
    base = get_settings().public_app_url.rstrip("/")
    url = f"{base}/invite/{token}"

    # Sent best-effort. A delivery failure must not fail the invitation:
    # the row is already committed and the admin has the link in the
    # response, so raising here would destroy a valid invitation over a
    # provider problem — and leave the email address unusable, since a
    # pending invite blocks re-inviting.
    subject, html, text = invitation_email(
        invited_by=current_user.display_name,
        role=invitation.role.value,
        url=url,
        expires_days=payload.expires_in_days,
    )
    try:
        email.send(to=invitation.email, subject=subject, html=html, text=text)
    except EmailError:
        logger.warning("invitation email to %s failed to send; the link is still valid", invitation.email)

    return InvitationCreated(
        **_to_summary(invitation).model_dump(),
        token=token,
        # Returned so the admin can copy it directly. Email is a convenience
        # on top of this, never a prerequisite.
        url=url,
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
