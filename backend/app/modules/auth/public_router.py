import logging

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.email.factory import get_email_sender
from app.email.messages import password_reset_email
from app.email.port import EmailError, EmailSender
from app.modules.auth.password_reset import EXPIRY_MINUTES, PasswordResetService
from app.modules.auth.router import get_password_reset_service
from app.schemas.auth import PasswordResetConfirm, PasswordResetRequest

logger = logging.getLogger(__name__)

# Under /public/ like every other unauthenticated route in the app (share
# links, invitation acceptance). Keeping that invariant means "what can be
# reached without a session?" is answerable by grepping one path prefix,
# rather than reading every router for a missing dependency.
router = APIRouter(prefix="/api/v1/public/auth", tags=["public-auth"])


@router.post("/password-reset", status_code=202)
def request_password_reset(
    payload: PasswordResetRequest,
    service: PasswordResetService = Depends(get_password_reset_service),
    email: EmailSender = Depends(get_email_sender),
) -> dict[str, str]:
    """Always answers 202, whether or not the address exists.

    Anything else — a 404, a different message, a noticeably faster reply —
    would turn "forgot password" into a way to discover who has an account
    here. The caller is told only that *if* the address is registered, a
    link is on its way."""
    result = service.request(payload.email)
    if result is not None:
        user, token = result
        base = get_settings().public_app_url.rstrip("/")
        subject, html, text = password_reset_email(
            url=f"{base}/reset-password/{token}", expires_minutes=EXPIRY_MINUTES
        )
        try:
            email.send(to=user.email, subject=subject, html=html, text=text)
        except EmailError:
            # Logged, not raised: the response must look identical either
            # way, and surfacing a provider failure here would also reveal
            # that the address exists.
            logger.warning("password reset email to %s failed to send", user.email)

    return {"message": "If that email has an account, a reset link is on its way."}


@router.post("/password-reset/{token}", status_code=204)
def confirm_password_reset(
    token: str,
    payload: PasswordResetConfirm,
    service: PasswordResetService = Depends(get_password_reset_service),
) -> None:
    """Deliberately doesn't sign the user in — they return to the login page
    and use the password they just set, keeping session creation on one path."""
    service.reset(token, payload.password)
