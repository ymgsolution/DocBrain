from fastapi import APIRouter, Depends

from app.modules.invitations.router import get_invitation_service
from app.modules.invitations.service import InvitationService
from app.schemas.auth import UserSummary
from app.schemas.invitation import InvitationAccept, PublicInvitation

# The second unauthenticated router in the application, and unavoidably so:
# the person accepting an invitation has no account yet — creating one is
# the entire point.
#
# The safeguards mirror the public share routes:
#   1. The token is the only input. There is no user id or email parameter
#      an attacker could substitute to claim a different account.
#   2. Unknown, expired, revoked and already-used tokens all return the same
#      404, so probing reveals nothing.
#   3. Accepting is single-use — the invite is marked accepted in the same
#      transaction that creates the user, so one link can never mint two
#      accounts.
router = APIRouter(prefix="/api/v1/public/invitations", tags=["public-invitations"])


@router.get("/{token}", response_model=PublicInvitation)
def peek_invitation(token: str, service: InvitationService = Depends(get_invitation_service)) -> PublicInvitation:
    invitation = service.peek(token)
    return PublicInvitation(
        email=invitation.email, role=invitation.role, expires_at=invitation.expires_at
    )


@router.post("/{token}/accept", response_model=UserSummary, status_code=201)
def accept_invitation(
    token: str,
    payload: InvitationAccept,
    service: InvitationService = Depends(get_invitation_service),
) -> UserSummary:
    """Creates the account and returns it — deliberately *without* logging
    the user in. They land on the sign-in page and enter the password they
    just chose, which confirms it works and keeps session creation on the
    single, well-tested login path."""
    user = service.accept(token, display_name=payload.display_name, password=payload.password)
    return UserSummary.model_validate(user, from_attributes=True)
