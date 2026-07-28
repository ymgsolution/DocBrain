from datetime import datetime

from app.core.exceptions import UnauthorizedError
from app.core.passwords import hash_password, verify_password
from app.core.security import create_access_token
from app.db.models import User, UserPreference
from app.db.models.enums import ThemePreference
from app.modules.auth.repository import AuthRepository

# Hashed once at import: verifying against this when no real hash exists
# keeps the "unknown email" path as slow as the "wrong password" path.
_DUMMY_HASH = hash_password("not-a-real-password-timing-equaliser")


class AuthService:
    def __init__(self, repository: AuthRepository) -> None:
        self.repository = repository

    def list_personas(self) -> list[User]:
        return self.repository.list_active_users()

    def login(self, email: str, password: str) -> tuple[str, datetime, User]:
        """One error message for every failure — unknown email, wrong
        password, deactivated account, or an invited user who never set a
        password. Distinguishing them would turn this endpoint into a way to
        discover which addresses have accounts here.

        verify_password is still called when the user is missing or has no
        hash, against a throwaway value, so a wrong email and a wrong
        password take the same time to answer. Otherwise the difference is
        measurable, and the fast path tells an attacker the email is
        unregistered."""
        user = self.repository.get_by_email(email.strip().lower())
        stored_hash = user.password_hash if user else None
        password_ok = verify_password(password, stored_hash or _DUMMY_HASH)

        if user is None or not user.is_active or not user.password_hash or not password_ok:
            raise UnauthorizedError("That email and password don't match an account.")

        token, expires_at = create_access_token(user.id, user.role.value)
        return token, expires_at, user

    def get_preferences(self, user: User) -> UserPreference:
        preferences = self.repository.get_preferences(user.id)
        if preferences is None:
            # Every seeded user gets one (scripts/seed.py); this only covers a
            # user created some other way, so preferences always resolve.
            preferences = UserPreference(user_id=user.id)
            self.repository.add_preferences(preferences)
            self.repository.db.commit()
            self.repository.db.refresh(preferences)
        return preferences

    def update_preferences(
        self, user: User, *, theme: ThemePreference | None, default_page_size: int | None
    ) -> UserPreference:
        preferences = self.get_preferences(user)
        if theme is not None:
            preferences.theme = theme
        if default_page_size is not None:
            preferences.default_page_size = default_page_size
        self.repository.db.commit()
        self.repository.db.refresh(preferences)
        return preferences
