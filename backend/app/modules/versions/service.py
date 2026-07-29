import uuid
from typing import BinaryIO

from fastapi import UploadFile

from app.core.exceptions import GoneError, NotFoundError, PermissionDeniedError, ValidationError
from app.db.models import ActivityEvent, AiJob, Document, DocumentVersion, User
from app.db.models.enums import ActivityEventType, AiJobType, DocumentStatus, UserRole
from app.modules.versions.repository import VersionRepository
from app.storage.checksum import sha256_of_stream
from app.storage.factory import get_storage
from app.storage.port import StoragePort
from app.utils.file_validation import (
    sniff_mime_type,
    validate_content_matches_extension,
    validate_extension,
    validate_size,
)


def _assert_can_upload_version(document: Document, user: User) -> None:
    if document.owner_id == user.id or user.role in (UserRole.REVIEWER, UserRole.ADMIN):
        return
    raise PermissionDeniedError("Only the owner, a reviewer, or an admin can upload a new version of this document.")


class VersionService:
    def __init__(self, repository: VersionRepository, storage: StoragePort) -> None:
        self.repository = repository
        self.storage = storage

    def _storage_for(self, provider: str) -> StoragePort:
        """The adapter that actually holds a given version's bytes.

        Prefers the injected `self.storage` whenever it already speaks that
        provider — which is the overwhelmingly common case, since it *is*
        the configured default. Only a version written under a different
        provider (i.e. before a STORAGE_PROVIDER change) falls through to
        the factory. Going straight to the factory unconditionally would
        quietly ignore the injected dependency, making it impossible to
        point this service at a different adapter (a test's temp directory,
        say) and have reads honour it."""
        if provider == self.storage.provider_name:
            return self.storage
        return get_storage(provider)

    def list_versions(self, document: Document) -> list[DocumentVersion]:
        return self.repository.list_for_document(document.id)

    def get_content(self, document: Document, version_number: int) -> tuple[DocumentVersion, BinaryIO]:
        version = self.repository.get(document.id, version_number)
        if version is None:
            raise NotFoundError("That version doesn't exist.")
        # Resolved by the version's own stamped provider, not self.storage
        # (today's configured default) — a version uploaded before a
        # STORAGE_PROVIDER flip still lives where it was actually written.
        storage = self._storage_for(version.storage_provider)
        try:
            stream = storage.open_for_read(version.storage_path)
        except FileNotFoundError as exc:
            raise GoneError("The file for this version is missing from storage.") from exc
        return version, stream

    def upload_version(
        self, document_id: uuid.UUID, *, file: UploadFile, change_note: str, current_user: User
    ) -> DocumentVersion:
        document = self.repository.get_document_for_update(document_id, current_user.organization_id)
        if document is None or document.status != DocumentStatus.ACTIVE:
            raise NotFoundError("This document doesn't exist or was deleted.")
        _assert_can_upload_version(document, current_user)

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

            version_number = self.repository.next_version_number(document_id)
            storage_path = self.storage.build_storage_path(document.id, version_number, file.filename or "upload")

            version = DocumentVersion(
                document_id=document.id,
                organization_id=current_user.organization_id,
                version_number=version_number,
                storage_path=storage_path,
                storage_provider=self.storage.provider_name,
                original_filename=file.filename or "upload",
                mime_type=mime_type,
                size_bytes=size_bytes,
                checksum_sha256=checksum,
                change_note=change_note,
                uploaded_by=current_user.id,
            )
            self.repository.add(version)
            self.repository.db.flush()
            document.current_version_id = version.id

            self.repository.db.add(
                ActivityEvent(
                    document_id=document.id,
                    organization_id=current_user.organization_id,
                    actor_id=current_user.id,
                    event_type=ActivityEventType.VERSION_UPLOADED,
                    summary=f"{current_user.display_name} uploaded version {version_number} of “{document.title}”",
                )
            )
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

        self.storage.commit(temp_path, storage_path)
        self.repository.db.refresh(version)
        return version

    def restore_version(
        self, document_id: uuid.UUID, version_number: int, *, change_note: str | None, current_user: User
    ) -> DocumentVersion:
        document = self.repository.get_document_for_update(document_id, current_user.organization_id)
        if document is None or document.status != DocumentStatus.ACTIVE:
            raise NotFoundError("This document doesn't exist or was deleted.")
        _assert_can_upload_version(document, current_user)

        source = self.repository.get(document_id, version_number)
        if source is None:
            raise NotFoundError("That version doesn't exist.")
        if document.current_version_id == source.id:
            raise ValidationError("This is already the current version.")

        new_version_number = self.repository.next_version_number(document_id)
        new_storage_path = self.storage.build_storage_path(document.id, new_version_number, source.original_filename)
        if source.storage_provider == self.storage.provider_name:
            # Fast path: source and destination are the same adapter, so a
            # native server-side copy applies (no bytes round-trip through
            # this process).
            self.storage.copy(source.storage_path, new_storage_path)
        else:
            # Source lives on a different provider than today's default
            # (e.g. restoring a version uploaded before a STORAGE_PROVIDER
            # flip) — copy() only works within one adapter, so fall back to
            # reading the source's bytes and writing them into the current
            # provider via the normal save_temp/commit path.
            source_storage = self._storage_for(source.storage_provider)
            with source_storage.open_for_read(source.storage_path) as stream:
                temp_path = self.storage.save_temp(stream)
            self.storage.commit(temp_path, new_storage_path)

        version = DocumentVersion(
            document_id=document.id,
            organization_id=current_user.organization_id,
            version_number=new_version_number,
            storage_path=new_storage_path,
            storage_provider=self.storage.provider_name,
            original_filename=source.original_filename,
            mime_type=source.mime_type,
            size_bytes=source.size_bytes,
            checksum_sha256=source.checksum_sha256,
            change_note=change_note or f"Restored from version {version_number}",
            uploaded_by=current_user.id,
            restored_from_version_id=source.id,
        )
        self.repository.add(version)
        self.repository.db.flush()
        document.current_version_id = version.id

        self.repository.db.add(
            ActivityEvent(
                document_id=document.id,
                organization_id=current_user.organization_id,
                actor_id=current_user.id,
                event_type=ActivityEventType.VERSION_RESTORED,
                summary=(
                    f"{current_user.display_name} restored version {version_number} "
                    f"as version {new_version_number} of “{document.title}”"
                ),
            )
        )
        # A restore copies bytes from `source`, so its extraction is
        # technically re-derivable rather than new content — enqueued anyway
        # for uniformity (every new document_versions row gets exactly one
        # EXTRACT job, no special-casing) rather than reusing `source`'s
        # extraction result. Cheap to re-run; not an AI call.
        self.repository.db.add(
            AiJob(
                job_type=AiJobType.EXTRACT,
                document_version_id=version.id,
                organization_id=current_user.organization_id,
            )
        )
        self.repository.db.commit()
        self.repository.db.refresh(version)
        return version
