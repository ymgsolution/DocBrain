import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User, UserPreference


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active_users(self, organization_id: uuid.UUID) -> list[User]:
        stmt = (
            select(User)
            .where(User.is_active.is_(True), User.organization_id == organization_id)
            .order_by(User.role, User.display_name)
        )
        return list(self.db.scalars(stmt))

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.scalar(stmt)

    def get_preferences(self, user_id: uuid.UUID) -> UserPreference | None:
        return self.db.get(UserPreference, user_id)

    def add_preferences(self, preferences: UserPreference) -> None:
        self.db.add(preferences)
