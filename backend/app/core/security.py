import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()


class InvalidTokenError(Exception):
    pass


def create_access_token(
    user_id: uuid.UUID, role: str, organization_id: uuid.UUID | None = None
) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.jwt_expires_minutes)
    claims = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    # Convenience only, e.g. so the frontend can show the org name without an
    # extra round-trip — never the source of truth. Every authorization
    # decision reads organization_id off the User row get_current_user
    # already re-fetches on every request, the same posture already used for
    # role (docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md, Part 4). Omitted from
    # the payload entirely, not set to null, for users not yet in an
    # organization.
    if organization_id is not None:
        claims["org_id"] = str(organization_id)
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
