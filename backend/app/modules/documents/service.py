import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import UploadFile

from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.db.models import ActivityEvent, Category, Document, DocumentVersion, User
from app.db.models.enums import ActivityEventType, DocumentStatus, UserRole
from app.modules.documents.repository import DocumentRepository
from app.storage.checksum import sha256_of_stream
from app.storage.local_adapter import LocalFileSystemStorage
from app.utils.file_validation import (
    sniff_mime_type,
    validate_content_matches_extension,
    validate_extension,
    validate_size,
)


def _assert_can_edit(document: Document, user: User) -> None:
    if document.owner_id == user.id or user.role in (UserRole.REVIEWER, UserRole.ADMIN):
        return
    raise PermissionDeniedError("Only the owner, a reviewer, or an admin can edit this document.")


def _assert_can_delete(document: Document, user: User) -> None:
    if document.owner_id == user.id or user.role == UserRole.ADMIN:
        return
    raise PermissionDeniedError("Only the owner or an admin can delete this document.")


def _default_review_date(category: Category) -> date | None:
    if category.default_review_period_days:
        return (datetime.now(timezone.utc) + timedelta(days=category.default_review_period_days)).date()
    return None


class DocumentService:
    def __init__(self, repository: DocumentRepository, storage: LocalFileSystemStorage) -> None:
        self.repository = repository
        self.storage = storage

    def create_document(
        self,
        *,
        file: UploadFile,
        title: str,
        category_id: uuid.UUID,
        description: str | None,
        tag_names: list[str],
        review_due_date: date | None,
        current_user: User,
    ) -> Document:
        category = self.repository.get_category(category_id)
        if category is None or category.is_archived:
            raise ValidationError(
                "That category doesn't exist or is archived.",
                fields=[{"field": "category_id", "message": "Invalid category."}],
            )

        ext = validate_extension(file.filename or "")
        raw = file.file
        sample = raw.read(2048)
        raw.seek(0)
        mime_type = sniff_mime_type(sample)
        validate_content_matches_extension(ext, mime_type)

        temp_path = self.storage.save_temp(raw)
        try:
            size_bytes = temp_path.stat().st_size
            validate_size(size_bytes)
            with open(temp_path, "rb") as f:
                checksum = sha256_of_stream(f)

            document = Document(
                title=title,
                description=description,
                category_id=category_id,
                owner_id=current_user.id,
                status=DocumentStatus.ACTIVE,
                review_due_date=review_due_date or _default_review_date(category),
            )
            self.repository.add(document)
            self.repository.db.flush()  # allocate document.id for the storage path

            storage_path = self.storage.build_storage_path(document.id, 1, file.filename or "upload")
            version = DocumentVersion(
                document_id=document.id,
                version_number=1,
                storage_path=storage_path,
                original_filename=file.filename or "upload",
                mime_type=mime_type,
                size_bytes=size_bytes,
                checksum_sha256=checksum,
                uploaded_by=current_user.id,
            )
            self.repository.db.add(version)
            self.repository.db.flush()
            document.current_version_id = version.id

            tags = self.repository.get_or_create_tags(tag_names)
            self.repository.add_tags(document.id, [t.id for t in tags])

            self.repository.db.add(
                ActivityEvent(
                    document_id=document.id,
                    actor_id=current_user.id,
                    event_type=ActivityEventType.CREATED,
                    summary=f"{current_user.display_name} uploaded “{title}” (v1)",
                )
            )

            self.repository.db.commit()
        except Exception:
            self.repository.db.rollback()
            self.storage.discard(temp_path)
            raise

        # File is moved into place only after the DB transaction commits, so a
        # DB failure never leaves an orphan file (§12.1).
        self.storage.commit(temp_path, storage_path)
        self.repository.db.refresh(document)
        return document

    def get_detail(self, document_id: uuid.UUID, *, include_deleted: bool = False) -> Document:
        document = (
            self.repository.get_any_by_id(document_id)
            if include_deleted
            else self.repository.get_active_by_id(document_id)
        )
        if document is None:
            raise NotFoundError("This document doesn't exist or was deleted.")
        return document

    def touch_last_accessed(self, document: Document) -> None:
        document.last_accessed_at = datetime.now(timezone.utc)
        self.repository.db.commit()

    def list_documents(self, **kwargs) -> tuple[list[Document], int]:
        return self.repository.list_documents(**kwargs)

    def list_trash(self, *, current_user: User, page: int, size: int) -> tuple[list[Document], int]:
        # Same scoping as soft-delete/restore (§3.4): Admin sees every trashed
        # document, everyone else sees only what they themselves deleted.
        owner_id = None if current_user.role == UserRole.ADMIN else current_user.id
        return self.repository.list_trash(owner_id=owner_id, page=page, size=size)

    def update_metadata(
        self,
        document_id: uuid.UUID,
        *,
        current_user: User,
        title: str | None,
        description: str | None,
        category_id: uuid.UUID | None,
        tag_names: list[str] | None,
        review_due_date: date | None,
        owner_id: uuid.UUID | None,
    ) -> Document:
        document = self.get_detail(document_id)
        _assert_can_edit(document, current_user)

        if owner_id is not None and current_user.role not in (UserRole.REVIEWER, UserRole.ADMIN):
            raise PermissionDeniedError("Only a reviewer or admin can reassign ownership.")

        if title is not None:
            document.title = title
        if description is not None:
            document.description = description
        if category_id is not None:
            category = self.repository.get_category(category_id)
            if category is None or category.is_archived:
                raise ValidationError(
                    "That category doesn't exist or is archived.",
                    fields=[{"field": "category_id", "message": "Invalid category."}],
                )
            document.category_id = category_id
        if review_due_date is not None:
            document.review_due_date = review_due_date
        if owner_id is not None:
            document.owner_id = owner_id
        if tag_names is not None:
            self.repository.clear_tags(document.id)
            tags = self.repository.get_or_create_tags(tag_names)
            self.repository.add_tags(document.id, [t.id for t in tags])

        self.repository.db.add(
            ActivityEvent(
                document_id=document.id,
                actor_id=current_user.id,
                event_type=ActivityEventType.METADATA_UPDATED,
                summary=f"{current_user.display_name} updated metadata for “{document.title}”",
            )
        )
        self.repository.db.commit()
        self.repository.db.refresh(document)
        return document

    def soft_delete(self, document_id: uuid.UUID, *, current_user: User) -> None:
        document = self.get_detail(document_id)
        _assert_can_delete(document, current_user)
        document.status = DocumentStatus.DELETED
        document.deleted_at = datetime.now(timezone.utc)
        document.deleted_by = current_user.id
        self.repository.db.add(
            ActivityEvent(
                document_id=document.id,
                actor_id=current_user.id,
                event_type=ActivityEventType.DELETED,
                summary=f"{current_user.display_name} moved “{document.title}” to Trash",
            )
        )
        self.repository.db.commit()

    def restore(self, document_id: uuid.UUID, *, current_user: User) -> Document:
        document = self.get_detail(document_id, include_deleted=True)
        if document.status != DocumentStatus.DELETED:
            raise ValidationError("This document isn't in Trash.")
        _assert_can_delete(document, current_user)  # same rule set as soft-delete, per §3.4

        document.status = DocumentStatus.ACTIVE
        document.deleted_at = None
        document.deleted_by = None
        self.repository.db.add(
            ActivityEvent(
                document_id=document.id,
                actor_id=current_user.id,
                event_type=ActivityEventType.RESTORED,
                summary=f"{current_user.display_name} restored “{document.title}” from Trash",
            )
        )
        self.repository.db.commit()
        self.repository.db.refresh(document)
        return document

    def hard_delete(self, document_id: uuid.UUID, *, current_user: User) -> None:
        if current_user.role != UserRole.ADMIN:
            raise PermissionDeniedError("Only an admin can permanently delete a document.")
        document = self.get_detail(document_id, include_deleted=True)
        if document.status != DocumentStatus.DELETED:
            raise ValidationError("Only documents already in Trash can be permanently deleted.")

        storage_paths = self.repository.list_version_storage_paths(document.id)

        document.current_version_id = None
        self.repository.db.commit()  # null the pointer before purge (§7.3)

        self.repository.db.delete(document)  # cascades to versions/tags/activity per FK ondelete
        self.repository.db.commit()

        for path in storage_paths:
            self.storage.delete(path)
