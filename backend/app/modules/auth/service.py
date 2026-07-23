from datetime import datetime

from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token
from app.db.models import User, UserPreference
from app.db.models.enums import ThemePreference
from app.modules.auth.repository import AuthRepository


class AuthService:
    def __init__(self, repository: AuthRepository) -> None:
        self.repository = repository

    def list_personas(self) -> list[User]:
        return self.repository.list_active_users()

    def login(self, email: str) -> tuple[str, datetime, User]:
        user = self.repository.get_by_email(email.strip().lower())
        if user is None or not user.is_active:
            raise UnauthorizedError("No account matches that email — pick a demo user below.")
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
