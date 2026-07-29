from datetime import datetime

from app.core.exceptions import UnauthorizedError
from app.core.passwords import hash_password, verify_password
from app.core.security import create_platform_admin_token
from app.db.models import PlatformAdmin
from app.modules.platform.repository import PlatformAdminRepository

# Hashed once at import, same timing-equalizer reasoning as
# auth/service.py::AuthService._DUMMY_HASH — an unknown email must take the
# same time to reject as a wrong password.
_DUMMY_HASH = hash_password("not-a-real-password-timing-equaliser")


class PlatformAuthService:
    def __init__(self, repository: PlatformAdminRepository) -> None:
        self.repository = repository

    def login(self, email: str, password: str) -> tuple[str, datetime, PlatformAdmin]:
        admin = self.repository.get_by_email(email.strip().lower())
        stored_hash = admin.password_hash if admin else None
        password_ok = verify_password(password, stored_hash or _DUMMY_HASH)

        if admin is None or not admin.is_active or not password_ok:
            raise UnauthorizedError("That email and password don't match a platform admin account.")

        token, expires_at = create_platform_admin_token(admin.id)
        return token, expires_at, admin
