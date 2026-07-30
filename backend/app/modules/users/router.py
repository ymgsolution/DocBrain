import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.db.models import User
from app.db.models.enums import UserRole
from app.db.session import get_db_session
from app.modules.users.repository import UserAdminRepository
from app.modules.users.service import UserAdminService
from app.schemas.auth import UserSummary
from app.schemas.user_admin import PagedUsers, UserAdminSummary, UserRoleUpdate

# Admin-only, and mounted under /admin rather than alongside /auth/users on
# purpose: /auth/users is the colleague directory every signed-in user may
# read, and it deliberately shows only active people. Everything here exposes
# strictly more (deactivated accounts, who cut them off) or changes who can
# get in at all, so it sits behind the strictest role and its own prefix.
router = APIRouter(prefix="/api/v1/admin/users", tags=["admin-users"])


def get_user_admin_service(db: Session = Depends(get_db_session)) -> UserAdminService:
    return UserAdminService(UserAdminRepository(db))


def _to_summary(user: User) -> UserAdminSummary:
    return UserAdminSummary(
        id=user.id,
        display_name=user.display_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        deactivated_at=user.deactivated_at,
        deactivated_by=(
            UserSummary.model_validate(user.deactivator, from_attributes=True)
            if user.deactivator is not None
            else None
        ),
    )


@router.get("", response_model=PagedUsers)
def list_users(
    search: str | None = Query(default=None, max_length=200),
    status: str = Query(default="active", pattern="^(active|inactive|all)$"),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=25, ge=1, le=100),
    service: UserAdminService = Depends(get_user_admin_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> PagedUsers:
    items, total = service.search(
        organization_id=current_user.organization_id, search=search, status=status, page=page, size=size
    )
    return PagedUsers(
        items=[_to_summary(u) for u in items],
        page=page,
        size=size,
        total=total,
        total_pages=(total + size - 1) // size if size else 0,
    )


# POST /deactivate and /reactivate rather than one PATCH {isActive: bool}:
# the two directions aren't symmetric. Deactivating is guarded and has side
# effects (kills outstanding reset tokens); reactivating is a plain flip.
# Naming them separately keeps that asymmetry visible at the call site.
@router.post("/{user_id}/deactivate", response_model=UserAdminSummary)
def deactivate_user(
    user_id: uuid.UUID,
    service: UserAdminService = Depends(get_user_admin_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> UserAdminSummary:
    return _to_summary(service.deactivate(user_id, actor=current_user))


@router.post("/{user_id}/reactivate", response_model=UserAdminSummary)
def reactivate_user(
    user_id: uuid.UUID,
    service: UserAdminService = Depends(get_user_admin_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> UserAdminSummary:
    return _to_summary(service.reactivate(user_id, actor=current_user))


@router.patch("/{user_id}/role", response_model=UserAdminSummary)
def change_user_role(
    user_id: uuid.UUID,
    payload: UserRoleUpdate,
    service: UserAdminService = Depends(get_user_admin_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> UserAdminSummary:
    return _to_summary(service.change_role(user_id, role=payload.role, actor=current_user))
