import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Invitation


class InvitationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, invitation: Invitation) -> Invitation:
        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)
        return invitation

    def list_all(self, organization_id: uuid.UUID) -> list[Invitation]:
        stmt = (
            select(Invitation)
            .where(Invitation.organization_id == organization_id)
            .order_by(Invitation.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get_by_id(self, invitation_id: uuid.UUID, organization_id: uuid.UUID) -> Invitation | None:
        stmt = select(Invitation).where(
            Invitation.id == invitation_id, Invitation.organization_id == organization_id
        )
        return self.db.scalar(stmt)

    def get_pending_by_email(self, email: str) -> Invitation | None:
        """An outstanding invite for this address, if one exists — used to
        stop an admin stacking duplicates for the same person."""
        now = datetime.now(timezone.utc)
        stmt = select(Invitation).where(
            Invitation.email == email,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
            Invitation.expires_at > now,
        )
        return self.db.scalar(stmt)

    def get_usable_by_token_hash(self, token_hash: str) -> Invitation | None:
        """Resolves a token only if the invite is still usable *right now*.

        All four conditions live in the query rather than in the caller, so
        there's no code path where an endpoint can forget one and let an
        expired, revoked or already-used invite through."""
        now = datetime.now(timezone.utc)
        stmt = select(Invitation).where(
            Invitation.token_hash == token_hash,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
            Invitation.expires_at > now,
        )
        return self.db.scalar(stmt)
