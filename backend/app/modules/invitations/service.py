import uuid
from datetime import datetime, timedelta, timezone

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.passwords import MIN_PASSWORD_LENGTH, hash_password
from app.db.models import Invitation, User
from app.db.models.enums import UserRole
from app.modules.auth.repository import AuthRepository
from app.modules.invitations.repository import InvitationRepository
from app.modules.shares.tokens import generate_token, hash_token

# Long enough to survive a weekend and a spam folder, short enough that a
# forgotten invite doesn't stay a live route into the workspace forever.
DEFAULT_EXPIRY_DAYS = 7
MAX_EXPIRY_DAYS = 30


class InvitationService:
    def __init__(self, repository: InvitationRepository, users: AuthRepository) -> None:
        self.repository = repository
        self.users = users

    def create(
        self, *, email: str, role: UserRole, expires_in_days: int, invited_by: User
    ) -> tuple[Invitation, str]:
        """Returns the row **and** the raw token — the only moment it exists
        in readable form, exactly like a share link."""
        if expires_in_days < 1 or expires_in_days > MAX_EXPIRY_DAYS:
            raise ValidationError(
                f"An invitation must expire between 1 and {MAX_EXPIRY_DAYS} days from now.",
                fields=[{"field": "expiresInDays", "message": f"Choose 1-{MAX_EXPIRY_DAYS} days."}],
            )

        normalised = email.strip().lower()
        if self.users.get_by_email(normalised) is not None:
            raise ConflictError(
                "Someone already has an account with that email.",
                fields=[{"field": "email", "message": "This email already has an account."}],
            )
        if self.repository.get_pending_by_email(normalised) is not None:
            raise ConflictError(
                "There's already a pending invitation for that email — revoke it first, or resend that one.",
                fields=[{"field": "email", "message": "An invitation is already pending."}],
            )

        token = generate_token()
        invitation = Invitation(
            token_hash=hash_token(token),
            email=normalised,
            role=role,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
            invited_by=invited_by.id,
        )
        return self.repository.add(invitation), token

    def list_all(self) -> list[Invitation]:
        return self.repository.list_all()

    def revoke(self, invitation_id: uuid.UUID) -> Invitation:
        invitation = self.repository.get_by_id(invitation_id)
        if invitation is None:
            raise NotFoundError("That invitation doesn't exist.")
        if invitation.accepted_at is not None:
            # Revoking after the fact would imply the account goes away,
            # which it doesn't. Deactivating that user is the real action.
            raise ValidationError("That invitation was already accepted — deactivate the user instead.")
        if invitation.revoked_at is None:
            invitation.revoked_at = datetime.now(timezone.utc)
            self.repository.db.commit()
            self.repository.db.refresh(invitation)
        return invitation

    def peek(self, token: str) -> Invitation:
        """What the accept page shows before anyone types a password. Returns
        the same NotFoundError for unknown, expired, revoked and already-used
        tokens, so a stranger probing links learns nothing."""
        invitation = self.repository.get_usable_by_token_hash(hash_token(token))
        if invitation is None:
            raise NotFoundError("This invitation is invalid, has expired, or has already been used.")
        return invitation

    def accept(self, token: str, *, display_name: str, password: str) -> User:
        """Creates the account. This is the only path that mints a user."""
        invitation = self.peek(token)

        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValidationError(
                f"Choose a password of at least {MIN_PASSWORD_LENGTH} characters.",
                fields=[{"field": "password", "message": f"At least {MIN_PASSWORD_LENGTH} characters."}],
            )
        # Re-checked here, not just at invite time: an account with this
        # address may have been created in the days since the invite was
        # sent, and two users sharing an email would break login entirely.
        if self.users.get_by_email(invitation.email) is not None:
            raise ConflictError("An account with that email already exists — try signing in instead.")

        user = User(
            email=invitation.email,
            display_name=display_name.strip(),
            role=invitation.role,
            is_active=True,
            password_hash=hash_password(password),
        )
        self.repository.db.add(user)
        self.repository.db.flush()

        # Marking accepted in the same transaction as the user's creation is
        # what makes the invite genuinely single-use — the two can't diverge.
        invitation.accepted_at = datetime.now(timezone.utc)
        invitation.accepted_user_id = user.id
        self.repository.db.commit()
        self.repository.db.refresh(user)
        return user
