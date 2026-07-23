import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import ThemePreference

if TYPE_CHECKING:
    from app.db.models.user import User


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    theme: Mapped[ThemePreference] = mapped_column(
        Enum(ThemePreference, name="theme_preference", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=ThemePreference.SYSTEM,
        server_default=ThemePreference.SYSTEM.value,
    )
    default_page_size: Mapped[int] = mapped_column(Integer, nullable=False, default=25, server_default="25")

    user: Mapped["User"] = relationship(back_populates="preferences")
