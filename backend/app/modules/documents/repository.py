import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Category, Document, DocumentExtractedText, DocumentTag, DocumentVersion, Tag, User
from app.db.models.enums import DocumentStatus


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _base_query(self):
        return select(Document).options(
            selectinload(Document.category),
            selectinload(Document.owner),
            selectinload(Document.current_version).selectinload(DocumentVersion.uploader),
            selectinload(Document.tags),
        )

    def _detail_query(self):
        # Only the single-document fetch needs extraction status (for the
        # Document Details "Analyzing…" badge) — added on top of
        # _base_query() rather than into it, so the paginated list endpoint
        # (DocumentSummary, which never serializes this) doesn't pay for an
        # eager-load it never uses.
        return self._base_query().options(
            selectinload(Document.current_version).selectinload(DocumentVersion.extracted_text),
            selectinload(Document.current_version).selectinload(DocumentVersion.analysis),
        )

    def get_active_by_id(self, document_id: uuid.UUID, organization_id: uuid.UUID) -> Document | None:
        stmt = self._detail_query().where(
            Document.id == document_id,
            Document.status == DocumentStatus.ACTIVE,
            Document.organization_id == organization_id,
        )
        return self.db.scalar(stmt)

    def get_any_by_id(self, document_id: uuid.UUID, organization_id: uuid.UUID) -> Document | None:
        stmt = self._detail_query().where(
            Document.id == document_id, Document.organization_id == organization_id
        )
        return self.db.scalar(stmt)

    def list_by_ids(self, document_ids: list[uuid.UUID], organization_id: uuid.UUID) -> list[Document]:
        """Similar Document Detection track — hydrates the Document rows a
        SimilarityService query already ranked by id, with the same
        eager-loading (_base_query) a listing endpoint gets. Order is not
        guaranteed to match document_ids; callers that need ranked order
        (e.g. by similarity score) re-sort using the input list themselves.

        organization_id is required here too, not just trusted from the
        caller's already-scoped query that produced document_ids — a second
        independent check on the actual rows returned, cheap insurance
        against a future caller passing in an unscoped id list."""
        if not document_ids:
            return []
        stmt = self._base_query().where(
            Document.id.in_(document_ids), Document.organization_id == organization_id
        )
        return list(self.db.scalars(stmt))

    def list_documents(
        self,
        *,
        organization_id: uuid.UUID,
        q: str | None,
        category_id: uuid.UUID | None,
        tag_ids: list[uuid.UUID] | None,
        owner_id: uuid.UUID | None,
        status: DocumentStatus,
        review_status: str | None,
        sort: str,
        page: int,
        size: int,
    ) -> tuple[list[Document], int]:
        stmt = self._base_query().where(Document.status == status, Document.organization_id == organization_id)

        if q:
            tsquery = func.plainto_tsquery("english", q)
            stmt = stmt.where(Document.search_vector.op("@@")(tsquery))
        if category_id:
            stmt = stmt.where(Document.category_id == category_id)
        if owner_id:
            stmt = stmt.where(Document.owner_id == owner_id)
        if tag_ids:
            matching_docs = (
                select(DocumentTag.document_id)
                .where(DocumentTag.tag_id.in_(tag_ids))
                .group_by(DocumentTag.document_id)
                .having(func.count(func.distinct(DocumentTag.tag_id)) == len(tag_ids))
            )
            stmt = stmt.where(Document.id.in_(matching_docs))
        if review_status == "overdue":
            stmt = stmt.where(Document.review_due_date < func.current_date())
        elif review_status == "due_soon":
            stmt = stmt.where(
                Document.review_due_date >= func.current_date(),
                Document.review_due_date <= func.current_date() + 30,
            )
        elif review_status == "ok":
            stmt = stmt.where(
                (Document.review_due_date.is_(None)) | (Document.review_due_date > func.current_date() + 30)
            )

        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(Document.id).order_by(None).subquery()
        )
        total = self.db.scalar(count_stmt) or 0

        if q:
            stmt = stmt.order_by(func.ts_rank_cd(Document.search_vector, func.plainto_tsquery("english", q)).desc())
        elif sort == "created_at":
            stmt = stmt.order_by(Document.created_at.desc())
        elif sort == "title":
            stmt = stmt.order_by(Document.title.asc())
        else:
            stmt = stmt.order_by(Document.updated_at.desc())

        stmt = stmt.offset(page * size).limit(size)
        items = list(self.db.scalars(stmt))
        return items, total

    def add(self, document: Document) -> None:
        self.db.add(document)

    def add_tags(self, document_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> None:
        for tag_id in tag_ids:
            self.db.add(DocumentTag(document_id=document_id, tag_id=tag_id))

    def clear_tags(self, document_id: uuid.UUID) -> None:
        self.db.query(DocumentTag).filter(DocumentTag.document_id == document_id).delete()

    def get_or_create_tags(self, names: list[str], organization_id: uuid.UUID) -> list[Tag]:
        tags = []
        for raw_name in names:
            normalized = raw_name.strip().lower()
            if not normalized:
                continue
            tag = self.db.scalar(
                select(Tag).where(Tag.normalized_name == normalized, Tag.organization_id == organization_id)
            )
            if tag is None:
                tag = Tag(name=raw_name.strip(), normalized_name=normalized, organization_id=organization_id)
                self.db.add(tag)
                self.db.flush()
            tags.append(tag)
        return tags

    def list_trash(
        self, *, organization_id: uuid.UUID, owner_id: uuid.UUID | None, page: int, size: int
    ) -> tuple[list[Document], int]:
        stmt = (
            select(Document)
            .options(
                selectinload(Document.category),
                selectinload(Document.owner),
                selectinload(Document.deleted_by_user),
            )
            .where(Document.status == DocumentStatus.DELETED, Document.organization_id == organization_id)
            .order_by(Document.deleted_at.desc())
        )
        if owner_id:
            stmt = stmt.where(Document.owner_id == owner_id)

        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(Document.id).order_by(None).subquery()
        )
        total = self.db.scalar(count_stmt) or 0

        stmt = stmt.offset(page * size).limit(size)
        items = list(self.db.scalars(stmt))
        return items, total

    def get_category(self, category_id: uuid.UUID, organization_id: uuid.UUID) -> Category | None:
        stmt = select(Category).where(Category.id == category_id, Category.organization_id == organization_id)
        return self.db.scalar(stmt)

    def get_assignable_owner(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> User | None:
        """A user who may be made the owner of this organization's document.

        Organization-scoped for the same reason get_category above is: without
        it, PATCH /documents/{id} would accept any user id at all and hand a
        document to someone in another tenant, whose name and email would then
        render in this organization's document list.

        Active-only deliberately. Ownership carries responsibility — reviews,
        deletion rights — and the colleague directory a picker draws from
        (AuthRepository.list_active_users) already shows only active people,
        so accepting a deactivated one could only come from a stale UI or a
        hand-made request.
        """
        stmt = select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
            User.is_active.is_(True),
        )
        return self.db.scalar(stmt)

    def storage_used_bytes(self, organization_id: uuid.UUID) -> int:
        """Total bytes on disk for an organization, for the storage-limit
        setting.

        Sums *every* version, deliberately — including superseded versions and
        versions of documents sitting in Trash. Those bytes really are still
        stored: soft delete only flips Document.status, and the files are
        removed from storage solely by hard_delete. Counting only what a user
        can currently see in the app would report a number the disk doesn't
        agree with (measured on the live data: 29.5 MB visible vs 47.9 MB
        actually stored for the original organization).

        Reads DocumentVersion.organization_id directly rather than joining
        through documents — the column is denormalized onto the row precisely
        so counting queries like this don't need the join, and it's indexed.

        COALESCE because SUM over zero rows is NULL, and a brand-new
        organization must report 0, not None.
        """
        stmt = select(func.coalesce(func.sum(DocumentVersion.size_bytes), 0)).where(
            DocumentVersion.organization_id == organization_id
        )
        return int(self.db.scalar(stmt) or 0)

    def list_version_storage_paths(self, document_id: uuid.UUID) -> list[tuple[str, str]]:
        stmt = select(DocumentVersion.storage_path, DocumentVersion.storage_provider).where(
            DocumentVersion.document_id == document_id
        )
        return [(path, provider) for path, provider in self.db.execute(stmt)]

    def list_extracted_text_paths(self, document_id: uuid.UUID) -> list[str]:
        """AI feature track — the `.txt` siblings live outside the DB cascade
        (DocumentExtractedText rows cascade-delete for free; the files on
        disk don't), so hard_delete needs these paths explicitly."""
        stmt = (
            select(DocumentExtractedText.extracted_text_path)
            .join(DocumentVersion, DocumentVersion.id == DocumentExtractedText.document_version_id)
            .where(DocumentVersion.document_id == document_id, DocumentExtractedText.extracted_text_path.is_not(None))
        )
        return list(self.db.scalars(stmt))
