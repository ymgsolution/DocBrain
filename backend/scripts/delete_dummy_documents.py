"""One-time housekeeping: soft-delete then permanently delete every document
with no real file anywhere (not on local disk, not in Supabase) — fabricated
rows from scripts/seed.py that were never backed with real bytes (a
pre-existing gap, unrelated to the storage migration). Confirmed before
running: none of these documents have any ai_jobs/document_extracted_text/
ai_document_analysis/document_vector_embeddings rows, so this has zero
AI-track impact; the only cascades are document_versions/document_tags/
activity_events, all via existing ON DELETE CASCADE.

Goes through DocumentService.soft_delete/hard_delete — the same code path
the real API uses — rather than raw SQL, so activity events, storage
cleanup calls, and permission checks all run exactly as they would through
a real admin request.

Usage: uv run python -m scripts.delete_dummy_documents
"""

import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.models.enums import UserRole
from app.db.session import SessionLocal
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.service import DocumentService
from app.storage.factory import get_storage


def _admin_for(db: Session, organization_id: uuid.UUID) -> User | None:
    """An active admin of *that document's* organization.

    The original picked the first ADMIN in the whole table and used it for
    every document. That predates multi-tenancy and is wrong twice over now:
    DocumentService scopes every lookup to `current_user.organization_id`, so
    documents outside that one admin's organization would silently 404 and be
    skipped; and acting on one organization's data under another's admin is
    exactly the boundary the rest of the codebase spends its effort enforcing.
    """
    return db.scalars(
        select(User).where(
            User.organization_id == organization_id,
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
        )
    ).first()


def main() -> None:
    db = SessionLocal()
    try:
        # NOTE: "has no supabase-backed version" was a sound proxy for
        # "fabricated seed row" at the time this ran, when the corpus had
        # already been migrated to Supabase. It is not a safe proxy in
        # general — anything uploaded while STORAGE_PROVIDER=local matches
        # too. Check what the query selects before running this again; as of
        # 2026-07-30 it selects nothing, since all 34 versions are on Supabase.
        dummies = db.execute(
            text(
                """
                SELECT d.id, d.organization_id FROM documents d
                WHERE NOT EXISTS (
                    SELECT 1 FROM document_versions dv
                    WHERE dv.document_id = d.id AND dv.storage_provider = 'supabase'
                )
                """
            )
        ).all()
        print(f"Found {len(dummies)} dummy documents to remove.")

        repository = DocumentRepository(db)
        service = DocumentService(repository, get_storage())

        admins: dict[uuid.UUID, User | None] = {}
        removed = 0
        skipped = 0
        for doc_id, organization_id in dummies:
            if organization_id not in admins:
                admins[organization_id] = _admin_for(db, organization_id)
            admin = admins[organization_id]
            if admin is None:
                # Organizations with no admin are a real state — see the
                # platform dashboard's "No admin" banner — so skip rather
                # than abort the whole sweep.
                print(f"skip (organization {organization_id} has no active admin): {doc_id}")
                skipped += 1
                continue

            document = repository.get_active_by_id(doc_id, organization_id)
            if document is None:
                print(f"skip (not active/already gone): {doc_id}")
                skipped += 1
                continue
            service.soft_delete(doc_id, current_user=admin)
            service.hard_delete(doc_id, current_user=admin)
            removed += 1

        print(f"\nDone. removed={removed}, skipped={skipped}, of {len(dummies)} found.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
