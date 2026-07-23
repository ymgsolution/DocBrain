import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Category, Document, DocumentTag, Tag


class TaxonomyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_categories(self, *, include_archived: bool) -> list[tuple[Category, int]]:
        stmt = (
            select(Category, func.count(Document.id))
            .outerjoin(Document, Document.category_id == Category.id)
            .group_by(Category.id)
            .order_by(Category.name)
        )
        if not include_archived:
            stmt = stmt.where(Category.is_archived.is_(False))
        return [(row[0], row[1]) for row in self.db.execute(stmt)]

    def get_category(self, category_id: uuid.UUID) -> Category | None:
        return self.db.get(Category, category_id)

    def get_category_document_count(self, category_id: uuid.UUID) -> int:
        stmt = select(func.count(Document.id)).where(Document.category_id == category_id)
        return self.db.scalar(stmt) or 0

    def get_category_by_slug(self, slug: str) -> Category | None:
        return self.db.scalar(select(Category).where(Category.slug == slug))

    def get_category_by_name_ci(self, name: str) -> Category | None:
        stmt = select(Category).where(func.lower(Category.name) == name.lower())
        return self.db.scalar(stmt)

    def add_category(self, category: Category) -> None:
        self.db.add(category)

    def delete_category(self, category: Category) -> None:
        self.db.delete(category)

    def list_tags(self, *, q: str | None, limit: int) -> list[Tag]:
        stmt = select(Tag).order_by(Tag.usage_count.desc(), Tag.name)
        if q:
            stmt = stmt.where(Tag.normalized_name.ilike(f"%{q.strip().lower()}%"))
        stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt))

    def get_tag(self, tag_id: uuid.UUID) -> Tag | None:
        return self.db.get(Tag, tag_id)

    def get_tag_by_normalized_name(self, normalized_name: str) -> Tag | None:
        return self.db.scalar(select(Tag).where(Tag.normalized_name == normalized_name))

    def list_document_tags_for_tag(self, tag_id: uuid.UUID) -> list[DocumentTag]:
        stmt = select(DocumentTag).where(DocumentTag.tag_id == tag_id)
        return list(self.db.scalars(stmt))

    def get_document_tag(self, document_id: uuid.UUID, tag_id: uuid.UUID) -> DocumentTag | None:
        stmt = select(DocumentTag).where(
            DocumentTag.document_id == document_id, DocumentTag.tag_id == tag_id
        )
        return self.db.scalar(stmt)

    def delete_tag(self, tag: Tag) -> None:
        self.db.delete(tag)
