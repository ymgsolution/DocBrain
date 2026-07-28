import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.db.models import UserPreference
from app.modules.auth.repository import AuthRepository
from app.modules.auth.password_reset import EXPIRY_MINUTES, PasswordResetService
from app.modules.auth.service import AuthService
from app.email.factory import get_email_sender
from app.email.messages import password_reset_email
from app.email.port import EmailError, EmailSender
from app.schemas.auth import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
    UserPreferencesOut,
    UserPreferencesUpdate,
    UserSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_auth_service(db: Session = Depends(get_db_session)) -> AuthService:
    return AuthService(AuthRepository(db))


def get_password_reset_service(db: Session = Depends(get_db_session)) -> PasswordResetService:
    return PasswordResetService(db, AuthRepository(db))


@router.get("/users", response_model=list[UserSummary])
def list_users(
    service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user),
) -> list[User]:
    """Colleague directory — powers the "owner" filter on Pending Reviews.

    The `get_current_user` dependency is the point of this endpoint's
    existence in its current form: it previously had none, so anyone on the
    internet could enumerate every user's name, email and role. Signed-in
    colleagues seeing each other is normal for a shared workspace; strangers
    harvesting the staff list is not.
    """
    return service.list_personas()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    token, expires_at, user = service.login(payload.email, payload.password)
    return TokenResponse(token=token, expires_at=expires_at, user=UserSummary.model_validate(user))


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


@router.get("/me", response_model=UserSummary)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/logout", status_code=204)
def logout() -> None:
    return None


@router.get("/me/preferences", response_model=UserPreferencesOut)
def get_my_preferences(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> UserPreference:
    return service.get_preferences(current_user)


@router.patch("/me/preferences", response_model=UserPreferencesOut)
def update_my_preferences(
    payload: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> UserPreference:
    return service.update_preferences(
        current_user, theme=payload.theme, default_page_size=payload.default_page_size
    )
