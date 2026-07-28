import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.db.models import UserPreference
from app.modules.auth.repository import AuthRepository
from app.modules.auth.password_reset import PasswordResetService
from app.modules.auth.service import AuthService
from app.schemas.auth import (
    LoginRequest,
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
