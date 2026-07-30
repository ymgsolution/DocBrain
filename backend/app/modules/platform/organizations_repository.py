import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentVersion, Organization, User
from app.db.models.enums import DocumentStatus


class OrganizationsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_with_stats(self) -> list[tuple[Organization, int, int, int, int]]:
        """(organization, user_count, active_user_count, document_count,
        storage_used_bytes) — counts only, never document titles/content.
        Correlated subqueries rather than a join+group-by: several unrelated
        tables (users, documents, document_versions) counted against one row
        each, which a join would multiply-count without a more elaborate
        distinct-count query."""
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
        # Every version's bytes, including superseded versions and documents
        # in Trash — the same rule as DocumentRepository.storage_used_bytes
        # (see its docstring for why). COALESCE so an organization with no
        # documents reports 0 rather than NULL.
        storage_used_bytes = (
            select(func.coalesce(func.sum(DocumentVersion.size_bytes), 0))
            .where(DocumentVersion.organization_id == Organization.id)
            .correlate(Organization)
            .scalar_subquery()
        )
        stmt = select(Organization, user_count, active_user_count, document_count, storage_used_bytes).order_by(
            Organization.created_at.desc()
        )
        return [(row[0], row[1], row[2], row[3], row[4]) for row in self.db.execute(stmt)]

    def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        return self.db.get(Organization, organization_id)

    def get_by_slug(self, slug: str) -> Organization | None:
        return self.db.scalar(select(Organization).where(Organization.slug == slug))

    def add(self, organization: Organization) -> None:
        self.db.add(organization)
