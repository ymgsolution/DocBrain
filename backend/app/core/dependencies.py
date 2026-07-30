import uuid
from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import PermissionDeniedError, UnauthorizedError
from app.core.security import InvalidTokenError, decode_access_token
from app.db.models import PlatformAdmin, User
from app.db.models.enums import UserRole
from app.db.session import get_db_session

# A real Security scheme (rather than a plain Header dependency) is what makes
# FastAPI's /docs render a single "Authorize" button instead of requiring the
# token to be pasted into every endpoint's parameters individually.
bearer_scheme = HTTPBearer(auto_error=False, description="Paste the token from POST /auth/login here.")
platform_bearer_scheme = HTTPBearer(
    auto_error=False, description="Paste the token from POST /platform/auth/login here."
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db_session),
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Missing or malformed Authorization header.")

    token = credentials.credentials.strip()
    try:
        claims = decode_access_token(token)
    except InvalidTokenError as exc:
        raise UnauthorizedError("Invalid or expired token.") from exc

    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Malformed token.") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("This account no longer exists or is inactive.")
    return user


def get_current_platform_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(platform_bearer_scheme),
    db: Session = Depends(get_db_session),
) -> PlatformAdmin:
    """Deliberately independent from get_current_user, not layered on top of
    it — a platform admin is never a User row (see PlatformAdmin's
    docstring), so there is no shared code path for the two to accidentally
    merge back together. The explicit `typ` check means a regular user's
    token is rejected here immediately, not merely because its `sub` fails
    to resolve against PlatformAdmin."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Missing or malformed Authorization header.")

    token = credentials.credentials.strip()
    try:
        claims = decode_access_token(token)
    except InvalidTokenError as exc:
        raise UnauthorizedError("Invalid or expired token.") from exc

    if claims.get("typ") != "platform_admin":
        raise UnauthorizedError("This token isn't a platform admin token.")

    try:
        admin_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Malformed token.") from exc

    admin = db.get(PlatformAdmin, admin_id)
    if admin is None or not admin.is_active:
        raise UnauthorizedError("This account no longer exists or is inactive.")
    return admin


def require_role(*roles: UserRole) -> Callable[[User], User]:
    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            allowed = ", ".join(r.value for r in roles)
            raise PermissionDeniedError(f"This action requires one of these roles: {allowed}.")
        return current_user

    return _dependency
