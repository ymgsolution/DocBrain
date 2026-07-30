import uuid
from datetime import datetime

from app.db.models.enums import UserRole
from app.schemas.auth import UserSummary
from app.schemas.base import CamelModel


class UserAdminSummary(CamelModel):
    """The admin view of a user. Strictly wider than UserSummary — it exposes
    is_active and the deactivation audit pair, which is exactly why the
    colleague directory keeps returning the narrower one."""

    id: uuid.UUID
    display_name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    deactivated_at: datetime | None = None
    deactivated_by: UserSummary | None = None


class PagedUsers(CamelModel):
    items: list[UserAdminSummary]
    page: int
    size: int
    total: int
    total_pages: int


class UserRoleUpdate(CamelModel):
    role: UserRole
