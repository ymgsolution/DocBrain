import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.auth import UserSummary
from app.schemas.base import CamelModel


class VersionSummary(CamelModel):
    id: uuid.UUID
    version_number: int
    original_filename: str
    size_bytes: int
    mime_type: str
    uploaded_at: datetime


class VersionDetail(CamelModel):
    id: uuid.UUID
    version_number: int
    is_current: bool
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    change_note: str | None
    uploaded_by: UserSummary
    uploaded_at: datetime
    restored_from_version_id: uuid.UUID | None


class VersionRestoreRequest(CamelModel):
    change_note: str | None = Field(default=None, max_length=500)
