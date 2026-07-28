from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.passwords import MIN_PASSWORD_LENGTH, hash_password
from app.db.models import PasswordResetToken, User
from app.modules.auth.repository import AuthRepository
from app.modules.shares.tokens import generate_token, hash_token

# Short by design. A reset link is used within moments of being requested;
# a long window is just a bigger opening for whoever reads that mailbox next.
EXPIRY_MINUTES = 30


class PasswordResetService:
    def __init__(self, db: Session, users: AuthRepository) -> None:
        self.db = db
        self.users = users

    def request(self, email: str) -> tuple[User, str] | None:
        """Returns the user and raw token when a reset should be emailed, or
        None when there's nothing to send.

        None rather than an error on purpose: the endpoint must answer
        identically whether or not the address exists, or "forgot password"
        becomes a way to discover who has an account. An inactive user, or
        one who never set a password, is treated the same way.
        """
        user = self.users.get_by_email(email.strip().lower())
        if user is None or not user.is_active:
            return None

        # Any previously issued link is invalidated. Otherwise requesting a
        # reset twice would leave two live tokens, and the older email
        # (possibly the one an attacker already has) would still work.
        self._invalidate_outstanding(user)

        token = generate_token()
        self.db.add(
            PasswordResetToken(
                token_hash=hash_token(token),
                user_id=user.id,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=EXPIRY_MINUTES),
            )
        )
        self.db.commit()
        return user, token

    def reset(self, token: str, new_password: str) -> User:
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise ValidationError(
                f"Choose a password of at least {MIN_PASSWORD_LENGTH} characters.",
                fields=[{"field": "password", "message": f"At least {MIN_PASSWORD_LENGTH} characters."}],
            )

        now = datetime.now(timezone.utc)
        row = self.db.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == hash_token(token),
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            )
        )
        if row is None or not row.user.is_active:
            raise NotFoundError("This reset link is invalid, has expired, or has already been used.")

        row.user.password_hash = hash_password(new_password)
        # Marked used in the same transaction as the password change, so one
        # link can never set two passwords.
        row.used_at = now
        self.db.commit()
        self.db.refresh(row.user)
        return row.user

    def _invalidate_outstanding(self, user: User) -> None:
        outstanding = self.db.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
        )
        for row in outstanding:
            row.used_at = datetime.now(timezone.utc)
