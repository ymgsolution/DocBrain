from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active_users(self) -> list[User]:
        stmt = select(User).where(User.is_active.is_(True)).order_by(User.role, User.display_name)
        return list(self.db.scalars(stmt))

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.scalar(stmt)
