import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import PayloadTooLargeError
from app.db.models import DocumentVersion, Organization

_BYTES_PER_MB = 1024 * 1024


def organization_storage_used_bytes(db: Session, organization_id: uuid.UUID) -> int:
    """Total bytes on disk for an organization.

    Sums *every* version — superseded versions and versions of documents
    sitting in Trash included — because those files genuinely are still
    stored. Soft delete only flips Document.status; the bytes are released
    solely by a permanent delete. A figure that quietly excluded them would
    disagree with the disk, and the limit is a disk limit.

    Reads DocumentVersion.organization_id directly rather than joining through
    documents: the column is denormalized onto the row precisely so counting
    queries don't need the join, and it is indexed.
    """
    stmt = select(func.coalesce(func.sum(DocumentVersion.size_bytes), 0)).where(
        DocumentVersion.organization_id == organization_id
    )
    return int(db.scalar(stmt) or 0)


def validate_organization_quota(db: Session, *, organization_id: uuid.UUID, incoming_bytes: int) -> None:
    """Reject an upload that would take the organization past its limit.

    The per-organization counterpart to file_validation.validate_size(), which
    caps a *single file*. Both are checked, and they are independent: a small
    file can still be refused by this one.

    Deliberately one shared function rather than the same few lines in each
    service. Three code paths add bytes — creating a document, uploading a new
    version, and restoring an old version (which physically copies the file
    and inserts a new row) — and enforcing only some of them would leave a
    trivial way around the limit.

    Raises PayloadTooLargeError (413) rather than a new error type: the upload
    dialog already handles 413, so this surfaces correctly with no frontend
    change. Only the wording differs from the too-big-file case.

    Not transactionally airtight against simultaneous uploads: two requests can
    both pass this check and jointly exceed the limit. Taking a row lock on the
    organization for every upload would serialise all of them for a small
    overage that the next upload refuses anyway — a bad trade at this scale.
    """
    organization = db.get(Organization, organization_id)
    if organization is None:
        # Impossible in practice: organization_id is NOT NULL with an
        # ON DELETE RESTRICT FK. Skip rather than crash an upload over a
        # bookkeeping check.
        return

    limit_bytes = organization.storage_limit_mb * _BYTES_PER_MB
    used_bytes = organization_storage_used_bytes(db, organization_id)
    if used_bytes + incoming_bytes <= limit_bytes:
        return

    raise PayloadTooLargeError(
        "Your organization has reached its storage limit. Please contact your administrator.",
        fields=[
            {
                "field": "file",
                "message": (
                    f"Using {used_bytes / _BYTES_PER_MB:.1f} MB of {organization.storage_limit_mb} MB. "
                    "Permanently deleting documents from Trash frees space."
                ),
            }
        ],
    )
