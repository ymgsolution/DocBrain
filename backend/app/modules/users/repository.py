import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.models.enums import UserRole


class UserAdminRepository:
    """Reads the user table the way an *administrator* needs to see it —
    deactivated people included.

    Deliberately separate from AuthRepository, whose list_active_users powers
    the colleague directory every signed-in user can call. Widening that one
    to return inactive rows would leak former staff to the whole workspace;
    keeping them apart means the two audiences can never drift into each
    other by accident.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id, User.organization_id == organization_id)
        return self.db.scalar(stmt)

    def _base_query(self, *, organization_id: uuid.UUID, search: str | None, status: str) -> Select:
        stmt = select(User).where(User.organization_id == organization_id)

        if status == "active":
            stmt = stmt.where(User.is_active.is_(True))
        elif status == "inactive":
            stmt = stmt.where(User.is_active.is_(False))
        # "all" adds no predicate.

        if search:
            # ILIKE over both columns: an admin looking for someone types
            # either half of what they see in the table, not a field name.
            # escape="\\" so a literal % or _ in the box stays literal
            # instead of silently becoming a wildcard.
            term = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            if term:
                pattern = f"%{term}%"
                stmt = stmt.where(
                    or_(
                        User.display_name.ilike(pattern, escape="\\"),
                        User.email.ilike(pattern, escape="\\"),
                    )
                )
        return stmt

    def search(
        self, *, organization_id: uuid.UUID, search: str | None, status: str, page: int, size: int
    ) -> tuple[list[User], int]:
        stmt = self._base_query(organization_id=organization_id, search=search, status=status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0

        # Active first, then by name: the people an admin is looking for are
        # nearly always the current ones. id is the tiebreaker so paging can't
        # repeat or skip a row when two users share a display name.
        stmt = stmt.order_by(User.is_active.desc(), User.display_name, User.id)
        stmt = stmt.offset(page * size).limit(size)
        return list(self.db.scalars(stmt)), total

    def count_active_admins(self, organization_id: uuid.UUID, *, excluding: uuid.UUID | None = None) -> int:
        """How many admins would still be able to administer *this
        organization*. `excluding` asks the question as it will be *after*
        the change under consideration.

        organization_id is required, not optional: without it, an org with
        zero admins of its own could be created as long as some other org
        still had active admins somewhere in the database — the lockout
        guard would never trip for the org that actually needs it."""
        stmt = select(func.count()).select_from(User).where(
            User.role == UserRole.ADMIN, User.is_active.is_(True), User.organization_id == organization_id
        )
        if excluding is not None:
            stmt = stmt.where(User.id != excluding)
        return self.db.scalar(stmt) or 0
