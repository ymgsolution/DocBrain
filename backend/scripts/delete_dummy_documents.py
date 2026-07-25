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

from sqlalchemy import select, text

from app.db.models import User
from app.db.models.enums import UserRole
from app.db.session import SessionLocal
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.service import DocumentService
from app.storage.factory import get_storage


def main() -> None:
    db = SessionLocal()
    try:
        admin = db.scalars(select(User).where(User.role == UserRole.ADMIN)).first()
        if admin is None:
            print("No ADMIN user found — aborting.")
            return

        dummy_ids = db.execute(
            text(
                """
                SELECT d.id FROM documents d
                WHERE NOT EXISTS (
                    SELECT 1 FROM document_versions dv
                    WHERE dv.document_id = d.id AND dv.storage_provider = 'supabase'
                )
                """
            )
        ).scalars().all()
        print(f"Found {len(dummy_ids)} dummy documents to remove.")

        repository = DocumentRepository(db)
        service = DocumentService(repository, get_storage())

        removed = 0
        for doc_id in dummy_ids:
            document = repository.get_active_by_id(doc_id)
            if document is None:
                print(f"skip (not active/already gone): {doc_id}")
                continue
            service.soft_delete(doc_id, current_user=admin)
            service.hard_delete(doc_id, current_user=admin)
            removed += 1

        print(f"\nDone. removed={removed}/{len(dummy_ids)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
