import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentVersion, Organization, User
from app.db.models.enums import DocumentStatus


class OrganizationsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_with_stats(self) -> list[tuple[Organization, int, int, int, int, int, int]]:
        """(organization, user_count, active_user_count, document_count,
        active_current_bytes, superseded_bytes, trashed_bytes) — counts and
        sizes only, never document titles/content. Correlated subqueries
        rather than a join+group-by: several unrelated tables (users,
        documents, document_versions) counted against one row each, which a
        join would multiply-count without a more elaborate distinct-count
        query."""
        user_count = (
            select(func.count(User.id))
            .where(User.organization_id == Organization.id)
            .correlate(Organization)
            .scalar_subquery()
        )
        active_user_count = (
            select(func.count(User.id))
            .where(User.organization_id == Organization.id, User.is_active.is_(True))
            .correlate(Organization)
            .scalar_subquery()
        )
        document_count = (
            select(func.count(Document.id))
            .where(Document.organization_id == Organization.id, Document.status == DocumentStatus.ACTIVE)
            .correlate(Organization)
            .scalar_subquery()
        )
        # Storage is returned as three parts rather than one total, because
        # the total on its own reads as wrong to the person looking at it:
        # measured on live data, the original organization shows 29.5 MB of
        # documents in the app but stores 47.9 MB — 38% of it superseded
        # versions and Trash. A settings screen that shows only "47.9 MB"
        # invites "your number is broken"; showing the split explains itself.
        #
        # The three are an exhaustive, disjoint partition of every version
        # (DocumentStatus has exactly ACTIVE and DELETED, and an active
        # document's version either is or isn't the current one), so the
        # caller can sum them for the total instead of running a fourth
        # subquery — which also makes it impossible for the parts to
        # disagree with the whole.
        def _version_bytes(*conditions):
            return (
                select(func.coalesce(func.sum(DocumentVersion.size_bytes), 0))
                .select_from(DocumentVersion)
                .join(Document, Document.id == DocumentVersion.document_id)
                .where(DocumentVersion.organization_id == Organization.id, *conditions)
                .correlate(Organization)
                .scalar_subquery()
            )

        active_current_bytes = _version_bytes(
            Document.status == DocumentStatus.ACTIVE,
            Document.current_version_id == DocumentVersion.id,
        )
        superseded_bytes = _version_bytes(
            Document.status == DocumentStatus.ACTIVE,
            Document.current_version_id.is_distinct_from(DocumentVersion.id),
        )
        trashed_bytes = _version_bytes(Document.status == DocumentStatus.DELETED)

        stmt = select(
            Organization,
            user_count,
            active_user_count,
            document_count,
            active_current_bytes,
            superseded_bytes,
            trashed_bytes,
        ).order_by(Organization.created_at.desc())
        return [tuple(row) for row in self.db.execute(stmt)]

    def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        return self.db.get(Organization, organization_id)

    def get_by_slug(self, slug: str) -> Organization | None:
        return self.db.scalar(select(Organization).where(Organization.slug == slug))

    def add(self, organization: Organization) -> None:
        self.db.add(organization)
