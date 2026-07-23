import uuid
from datetime import datetime

from pydantic import EmailStr

from app.db.models.enums import UserRole
from app.schemas.base import CamelModel


class UserSummary(CamelModel):
    id: uuid.UUID
    display_name: str
    email: str
    role: UserRole


class LoginRequest(CamelModel):
    email: EmailStr


class TokenResponse(CamelModel):
    token: str
    expires_at: datetime
    user: UserSummary
