import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PlatformAdmin


class PlatformAdminRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> PlatformAdmin | None:
        return self.db.scalar(select(PlatformAdmin).where(PlatformAdmin.email == email))

    def get_by_id(self, admin_id: uuid.UUID) -> PlatformAdmin | None:
        return self.db.get(PlatformAdmin, admin_id)
