import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Document, Organization, User
from app.db.models.enums import DocumentStatus


class OrganizationsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_with_stats(self) -> list[tuple[Organization, int, int, int]]:
        """(organization, user_count, active_user_count, document_count) —
        counts only, never document titles/content. Correlated subqueries
        rather than a join+group-by: three unrelated tables (users,
        documents) counted against one row each, which a join would
        multiply-count without a more elaborate distinct-count query."""
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
        stmt = select(Organization, user_count, active_user_count, document_count).order_by(
            Organization.created_at.desc()
        )
        return [(row[0], row[1], row[2], row[3]) for row in self.db.execute(stmt)]

    def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        return self.db.get(Organization, organization_id)

    def get_by_slug(self, slug: str) -> Organization | None:
        return self.db.scalar(select(Organization).where(Organization.slug == slug))

    def add(self, organization: Organization) -> None:
        self.db.add(organization)
