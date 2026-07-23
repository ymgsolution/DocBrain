from datetime import datetime

from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token
from app.db.models import User
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
