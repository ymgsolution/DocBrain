import uuid

from app.db.models import Document, DocumentVersion
from app.schemas.auth import UserSummary
from app.schemas.document import CategorySummary, DocumentDetail, DocumentSummary, TagSummary
from app.schemas.trash import TrashedDocumentItem
from app.schemas.version import VersionDetail, VersionSummary


def to_version_summary(version: DocumentVersion) -> VersionSummary:
    return VersionSummary(
        id=version.id,
        version_number=version.version_number,
        original_filename=version.original_filename,
        size_bytes=version.size_bytes,
        mime_type=version.mime_type,
        uploaded_at=version.uploaded_at,
    )


def to_version_detail(version: DocumentVersion, current_version_id: uuid.UUID | None) -> VersionDetail:
    return VersionDetail(
        id=version.id,
        version_number=version.version_number,
        is_current=version.id == current_version_id,
        original_filename=version.original_filename,
        mime_type=version.mime_type,
        size_bytes=version.size_bytes,
        checksum_sha256=version.checksum_sha256,
        change_note=version.change_note,
        uploaded_by=UserSummary.model_validate(version.uploader),
        uploaded_at=version.uploaded_at,
        restored_from_version_id=version.restored_from_version_id,
    )


def to_document_summary(document: Document) -> DocumentSummary:
    return DocumentSummary(
        id=document.id,
        title=document.title,
        description=document.description,
        category=CategorySummary.model_validate(document.category),
        owner=UserSummary.model_validate(document.owner),
        current_version=to_version_summary(document.current_version) if document.current_version else None,
        version_count=document.version_count,
        review_due_date=document.review_due_date,
        updated_at=document.updated_at,
        created_at=document.created_at,
    )


def to_document_detail(document: Document) -> DocumentDetail:
    return DocumentDetail(
        id=document.id,
        title=document.title,
        description=document.description,
        category=CategorySummary.model_validate(document.category),
        owner=UserSummary.model_validate(document.owner),
        current_version=to_version_summary(document.current_version) if document.current_version else None,
        version_count=document.version_count,
        review_due_date=document.review_due_date,
        updated_at=document.updated_at,
        created_at=document.created_at,
        tags=[TagSummary.model_validate(t) for t in document.tags],
        last_reviewed_at=document.last_reviewed_at,
        last_accessed_at=document.last_accessed_at,
        status=document.status,
    )


def to_trashed_document_item(document: Document) -> TrashedDocumentItem:
    assert document.deleted_at is not None  # invariant: only DELETED documents reach this mapper
    return TrashedDocumentItem(
        id=document.id,
        title=document.title,
        category=CategorySummary.model_validate(document.category),
        owner=UserSummary.model_validate(document.owner),
        deleted_at=document.deleted_at,
        deleted_by=UserSummary.model_validate(document.deleted_by_user) if document.deleted_by_user else None,
    )
