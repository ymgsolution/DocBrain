import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models import PasswordResetToken, User
from app.db.models.enums import UserRole
from app.modules.users.repository import UserAdminRepository

# Mirrors the documents list. Kept here rather than inlined in the router so
# the service can be driven directly from a test or a script with the same
# defaults the API uses.
DEFAULT_PAGE_SIZE = 25
VALID_STATUSES = ("active", "inactive", "all")


class UserAdminService:
    """Deactivation, reactivation and role changes.

    Every method here is one `UPDATE users SET ...` guarded by the two ways
    an admin can lock the workspace out of its own administration:

      * turning off / demoting *yourself* — the next request 401s or 403s,
        and the page you'd use to undo it is the one you just lost;
      * turning off / demoting the *last* admin — nobody can administer
        anything again, and the only repair is hand-written SQL against
        production.

    Both are cheap to check and expensive to recover from, which is why they
    live in the service rather than being left to the UI to hide.
    """

    def __init__(self, repository: UserAdminRepository) -> None:
        self.repository = repository

    def search(
        self, *, search: str | None = None, status: str = "active", page: int = 0, size: int = DEFAULT_PAGE_SIZE
    ) -> tuple[list[User], int]:
        if status not in VALID_STATUSES:
            raise ValidationError(f"Status must be one of: {', '.join(VALID_STATUSES)}.")
        return self.repository.search(search=search, status=status, page=page, size=size)

    def _get(self, user_id: uuid.UUID) -> User:
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("That user doesn't exist.")
        return user

    def deactivate(self, user_id: uuid.UUID, *, actor: User) -> User:
        user = self._get(user_id)

        if user.id == actor.id:
            raise ValidationError(
                "You can't deactivate your own account — ask another admin to do it.",
            )
        if user.role == UserRole.ADMIN and self.repository.count_active_admins(excluding=user.id) == 0:
            raise ValidationError(
                "This is the last active admin. Promote someone else to admin first, "
                "otherwise nobody will be able to manage the workspace.",
            )

        if user.is_active:
            user.is_active = False
            user.deactivated_at = datetime.now(timezone.utc)
            user.deactivated_by = actor.id
            # A live reset link would otherwise sit in their inbox outliving
            # their access. Login already refuses an inactive account, so this
            # isn't a hole today — it's dead state that shouldn't be left to
            # become one if the login checks are ever reordered.
            self._invalidate_password_resets(user)
            self.repository.db.commit()
            self.repository.db.refresh(user)
        return user

    def reactivate(self, user_id: uuid.UUID, *, actor: User) -> User:
        user = self._get(user_id)
        if not user.is_active:
            user.is_active = True
            user.deactivated_at = None
            user.deactivated_by = None
            self.repository.db.commit()
            self.repository.db.refresh(user)
        return user

    def change_role(self, user_id: uuid.UUID, *, role: UserRole, actor: User) -> User:
        user = self._get(user_id)

        if user.role == role:
            return user
        if user.id == actor.id:
            # Same lockout as deactivating yourself, one step slower: the
            # demotion succeeds, then every admin screen 403s.
            raise ValidationError(
                "You can't change your own role — ask another admin to do it.",
            )
        if (
            user.role == UserRole.ADMIN
            and user.is_active
            and self.repository.count_active_admins(excluding=user.id) == 0
        ):
            raise ValidationError(
                "This is the last active admin. Promote someone else to admin first.",
            )

        user.role = role
        self.repository.db.commit()
        self.repository.db.refresh(user)
        return user

    def _invalidate_password_resets(self, user: User) -> None:
        outstanding = self.repository.db.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
        )
        for row in outstanding:
            row.used_at = datetime.now(timezone.utc)
