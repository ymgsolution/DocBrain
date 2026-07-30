import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_platform_admin
from app.db.models import PlatformAdmin
from app.db.session import get_db_session
from app.modules.auth.repository import AuthRepository
from app.modules.platform.auth_service import PlatformAuthService
from app.modules.platform.organizations_repository import OrganizationsRepository
from app.modules.platform.organizations_service import OrganizationsService
from app.modules.platform.repository import PlatformAdminRepository
from app.schemas.platform import (
    FirstAdminCreate,
    FirstAdminCreated,
    OrganizationCreate,
    OrganizationCreated,
    OrganizationSettings,
    OrganizationStats,
    PlatformAdminSummary,
    PlatformLoginRequest,
    PlatformTokenResponse,
)

# A fully separate namespace from /api/v1/* — see PlatformAdmin's docstring
# for why platform admins are kept structurally apart from regular users.
router = APIRouter(prefix="/api/v1/platform", tags=["platform"])


def get_platform_auth_service(db: Session = Depends(get_db_session)) -> PlatformAuthService:
    return PlatformAuthService(PlatformAdminRepository(db))


def get_organizations_service(db: Session = Depends(get_db_session)) -> OrganizationsService:
    return OrganizationsService(OrganizationsRepository(db), AuthRepository(db))


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


@router.get("/organizations", response_model=list[OrganizationStats])
def list_organizations(
    service: OrganizationsService = Depends(get_organizations_service),
    current_admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> list[OrganizationStats]:
    return [
        OrganizationStats(
            id=org.id,
            name=org.name,
            slug=org.slug,
            created_at=org.created_at,
            user_count=user_count,
            active_user_count=active_user_count,
            document_count=document_count,
            settings=OrganizationSettings(
                ai_suggestions_enabled=org.ai_suggestions_enabled,
                duplicate_detection_enabled=org.duplicate_detection_enabled,
                storage_limit_mb=org.storage_limit_mb,
            ),
            storage_used_bytes=storage_used_bytes,
        )
        for org, user_count, active_user_count, document_count, storage_used_bytes in service.list_organizations()
    ]


@router.post("/organizations", response_model=OrganizationCreated, status_code=201)
def create_organization(
    payload: OrganizationCreate,
    service: OrganizationsService = Depends(get_organizations_service),
    current_admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> OrganizationCreated:
    organization = service.create_organization(name=payload.name)
    return OrganizationCreated(
        id=organization.id, name=organization.name, slug=organization.slug, created_at=organization.created_at
    )


@router.post("/organizations/{organization_id}/admins", response_model=FirstAdminCreated, status_code=201)
def create_first_admin(
    organization_id: uuid.UUID,
    payload: FirstAdminCreate,
    service: OrganizationsService = Depends(get_organizations_service),
    current_admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> FirstAdminCreated:
    admin = service.create_first_admin(
        organization_id, email=payload.email, display_name=payload.display_name, password=payload.password
    )
    return FirstAdminCreated(id=admin.id, email=admin.email, display_name=admin.display_name)
