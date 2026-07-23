from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService
from app.schemas.auth import LoginRequest, TokenResponse, UserSummary

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_auth_service(db: Session = Depends(get_db_session)) -> AuthService:
    return AuthService(AuthRepository(db))


@router.get("/users", response_model=list[UserSummary])
def list_users(service: AuthService = Depends(get_auth_service)) -> list[User]:
    return service.list_personas()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    token, expires_at, user = service.login(payload.email)
    return TokenResponse(token=token, expires_at=expires_at, user=UserSummary.model_validate(user))


@router.get("/me", response_model=UserSummary)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/logout", status_code=204)
def logout() -> None:
    return None
