from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_platform_admin
from app.db.models import PlatformAdmin
from app.db.session import get_db_session
from app.modules.platform.auth_service import PlatformAuthService
from app.modules.platform.repository import PlatformAdminRepository
from app.schemas.platform import PlatformAdminSummary, PlatformLoginRequest, PlatformTokenResponse

# A fully separate namespace from /api/v1/* — see PlatformAdmin's docstring
# for why platform admins are kept structurally apart from regular users.
router = APIRouter(prefix="/api/v1/platform", tags=["platform"])


def get_platform_auth_service(db: Session = Depends(get_db_session)) -> PlatformAuthService:
    return PlatformAuthService(PlatformAdminRepository(db))


@router.post("/auth/login", response_model=PlatformTokenResponse)
def login(
    payload: PlatformLoginRequest, service: PlatformAuthService = Depends(get_platform_auth_service)
) -> PlatformTokenResponse:
    token, expires_at, admin = service.login(payload.email, payload.password)
    return PlatformTokenResponse(
        token=token, expires_at=expires_at, admin=PlatformAdminSummary.model_validate(admin, from_attributes=True)
    )


@router.get("/auth/me", response_model=PlatformAdminSummary)
def me(current_admin: PlatformAdmin = Depends(get_current_platform_admin)) -> PlatformAdmin:
    return current_admin
