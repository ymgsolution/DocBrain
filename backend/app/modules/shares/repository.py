import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ShareLink


class ShareLinkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, link: ShareLink) -> ShareLink:
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def list_for_document(self, document_id: uuid.UUID) -> list[ShareLink]:
        stmt = (
            select(ShareLink)
            .where(ShareLink.document_id == document_id)
            .order_by(ShareLink.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get_by_id(self, link_id: uuid.UUID) -> ShareLink | None:
        return self.db.get(ShareLink, link_id)

    def get_usable_by_token_hash(self, token_hash: str) -> ShareLink | None:
        """The public lookup: resolves a token only if the link is still
        usable *right now*.

        Expiry and revocation are filtered in the query itself, not checked
        by the caller afterwards — so there is no code path where an
        endpoint can forget one of the two and serve a document it
        shouldn't. `document` and `document_version` are eager-loaded
        because the public endpoints always need both, and the document's
        own status still has to be checked by the caller (a soft-deleted
        document must not stay reachable through an old link)."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(ShareLink)
            .where(
                ShareLink.token_hash == token_hash,
                ShareLink.revoked_at.is_(None),
                ShareLink.expires_at > now,
            )
            .options(selectinload(ShareLink.document), selectinload(ShareLink.document_version))
        )
        return self.db.scalar(stmt)

    def revoke(self, link: ShareLink) -> ShareLink:
        # Timestamped rather than deleted, so the owner's list still shows
        # that the link existed and when it was withdrawn.
        link.revoked_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(link)
        return link

    def record_view(self, link: ShareLink) -> None:
        link.view_count += 1
        link.last_viewed_at = datetime.now(timezone.utc)
        self.db.commit()
