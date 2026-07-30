import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import UploadFile

from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.db.models import ActivityEvent, AiJob, Category, Document, DocumentVersion, User
from app.db.models.enums import ActivityEventType, AiJobType, DocumentStatus, UserRole
from app.modules.documents.repository import DocumentRepository
from app.storage.checksum import sha256_of_stream
from app.storage.factory import get_storage
from app.storage.port import StoragePort
from app.utils.storage_quota import validate_organization_quota
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
    def __init__(self, repository: DocumentRepository, storage: StoragePort) -> None:
        self.repository = repository
        self.storage = storage

    def _storage_for(self, provider: str) -> StoragePort:
        """Mirrors VersionService._storage_for — prefer the injected adapter
        when it already speaks this version's provider, fall back to the
        factory only for a genuinely different one (see its docstring)."""
        if provider == self.storage.provider_name:
            return self.storage
        return get_storage(provider)

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
        category = self.repository.get_category(category_id, current_user.organization_id)
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

        # Size-based validation sits in its own block, before anything is
        # written. Both checks need the real byte count, which only exists
        # once the upload has been streamed to a temp file — a client-declared
        # size can't be trusted. Kept out of the transaction block below
        # because a rejection here has written no rows, so there is nothing to
        # roll back: only the temp file needs discarding. (Rolling back
        # regardless would also unwind whatever the caller's session was
        # already holding, which is not this function's business.)
        try:
            size_bytes = temp_path.stat().st_size
            validate_size(size_bytes)
            validate_organization_quota(
                self.repository.db,
                organization_id=current_user.organization_id,
                incoming_bytes=size_bytes,
            )
        except Exception:
            self.storage.discard(temp_path)
            raise

        try:
            with open(temp_path, "rb") as f:
                checksum = sha256_of_stream(f)

            document = Document(
                title=title,
                description=description,
                category_id=category_id,
                owner_id=current_user.id,
                organization_id=current_user.organization_id,
                status=DocumentStatus.ACTIVE,
                review_due_date=review_due_date or _default_review_date(category),
            )
            self.repository.add(document)
            self.repository.db.flush()  # allocate document.id for the storage path

            storage_path = self.storage.build_storage_path(document.id, 1, file.filename or "upload")
            version = DocumentVersion(
                document_id=document.id,
                organization_id=current_user.organization_id,
                version_number=1,
                storage_path=storage_path,
                storage_provider=self.storage.provider_name,
                original_filename=file.filename or "upload",
                mime_type=mime_type,
                size_bytes=size_bytes,
                checksum_sha256=checksum,
                uploaded_by=current_user.id,
            )
            self.repository.db.add(version)
            self.repository.db.flush()
            document.current_version_id = version.id

            tags = self.repository.get_or_create_tags(tag_names, current_user.organization_id)
            self.repository.add_tags(document.id, [t.id for t in tags])

            self.repository.db.add(
                ActivityEvent(
                    document_id=document.id,
                    organization_id=current_user.organization_id,
                    actor_id=current_user.id,
                    event_type=ActivityEventType.CREATED,
                    summary=f"{current_user.display_name} uploaded “{title}” (v1)",
                )
            )
            # AI feature track: queued here, processed out-of-band by the
            # worker — never inline, so a slow/failing extraction can't
            # affect this request's latency or success.
            self.repository.db.add(
                AiJob(
                    job_type=AiJobType.EXTRACT,
                    document_version_id=version.id,
                    organization_id=current_user.organization_id,
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

    def get_detail(
        self, document_id: uuid.UUID, organization_id: uuid.UUID, *, include_deleted: bool = False
    ) -> Document:
        # organization_id is the isolation boundary for this whole module: a
        # document belonging to another organization must 404 exactly like a
        # nonexistent one, never leak via a distinguishable error
        # (docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md, Part 6). Every other
        # module reaches a Document only through this method or the
        # repository calls right below it, so fixing the check here closes
        # the gap everywhere at once.
        document = (
            self.repository.get_any_by_id(document_id, organization_id)
            if include_deleted
            else self.repository.get_active_by_id(document_id, organization_id)
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
        # document in their own org, everyone else sees only what they
        # themselves deleted.
        owner_id = None if current_user.role == UserRole.ADMIN else current_user.id
        return self.repository.list_trash(
            organization_id=current_user.organization_id, owner_id=owner_id, page=page, size=size
        )

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
        document = self.get_detail(document_id, current_user.organization_id)
        _assert_can_edit(document, current_user)

        if owner_id is not None and current_user.role not in (UserRole.REVIEWER, UserRole.ADMIN):
            raise PermissionDeniedError("Only a reviewer or admin can reassign ownership.")

        if title is not None:
            document.title = title
        if description is not None:
            document.description = description
        if category_id is not None:
            category = self.repository.get_category(category_id, current_user.organization_id)
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
            tags = self.repository.get_or_create_tags(tag_names, current_user.organization_id)
            self.repository.add_tags(document.id, [t.id for t in tags])

        self.repository.db.add(
            ActivityEvent(
                document_id=document.id,
                organization_id=current_user.organization_id,
                actor_id=current_user.id,
                event_type=ActivityEventType.METADATA_UPDATED,
                summary=f"{current_user.display_name} updated metadata for “{document.title}”",
            )
        )
        self.repository.db.commit()
        self.repository.db.refresh(document)
        return document

    def soft_delete(self, document_id: uuid.UUID, *, current_user: User) -> None:
        document = self.get_detail(document_id, current_user.organization_id)
        _assert_can_delete(document, current_user)
        document.status = DocumentStatus.DELETED
        document.deleted_at = datetime.now(timezone.utc)
        document.deleted_by = current_user.id
        self.repository.db.add(
            ActivityEvent(
                document_id=document.id,
                organization_id=current_user.organization_id,
                actor_id=current_user.id,
                event_type=ActivityEventType.DELETED,
                summary=f"{current_user.display_name} moved “{document.title}” to Trash",
            )
        )
        self.repository.db.commit()

    def restore(self, document_id: uuid.UUID, *, current_user: User) -> Document:
        document = self.get_detail(document_id, current_user.organization_id, include_deleted=True)
        if document.status != DocumentStatus.DELETED:
            raise ValidationError("This document isn't in Trash.")
        _assert_can_delete(document, current_user)  # same rule set as soft-delete, per §3.4

        document.status = DocumentStatus.ACTIVE
        document.deleted_at = None
        document.deleted_by = None
        self.repository.db.add(
            ActivityEvent(
                document_id=document.id,
                organization_id=current_user.organization_id,
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
        document = self.get_detail(document_id, current_user.organization_id, include_deleted=True)
        if document.status != DocumentStatus.DELETED:
            raise ValidationError("Only documents already in Trash can be permanently deleted.")

        # (path, storage_provider) pairs, not just paths — a version written
        # under a since-changed STORAGE_PROVIDER default must still be
        # deleted from the provider that actually holds it (see
        # storage_provider column on DocumentVersion), not wherever
        # self.storage currently points.
        storage_paths = self.repository.list_version_storage_paths(document.id)
        # AI feature track: DocumentExtractedText/AiJob rows cascade-delete
        # for free via FK ondelete, but the .txt files on disk don't — same
        # reason storage_paths above needs collecting before the purge.
        # Extracted-text files aren't provider-tagged (they're a short-lived
        # derived artifact written moments after the original upload, not a
        # long-lived user-facing read) — deleted via self.storage, same as
        # before; a leftover orphan .txt on the "wrong" provider after a
        # STORAGE_PROVIDER flip is a low-severity cleanup gap, not data loss.
        extracted_text_paths = self.repository.list_extracted_text_paths(document.id)

        document.current_version_id = None
        self.repository.db.commit()  # null the pointer before purge (§7.3)

        self.repository.db.delete(document)  # cascades to versions/tags/activity per FK ondelete
        self.repository.db.commit()

        for path, provider in storage_paths:
            self._storage_for(provider).delete(path)
        for path in extracted_text_paths:
            self.storage.delete(path)
