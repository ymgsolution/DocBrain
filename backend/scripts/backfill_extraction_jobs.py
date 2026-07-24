"""One-time backfill: enqueue an EXTRACT job for every existing ACTIVE
document's current version that predates the extraction pipeline — one with
neither an ai_jobs row nor a document_extracted_text row yet. Safe to re-run:
anything already covered (job queued, or already extracted) is skipped.

Usage: uv run python -m scripts.backfill_extraction_jobs
"""

from sqlalchemy import select

from app.ai_jobs.repository import AiJobRepository
from app.db.models import AiJob, Document, DocumentExtractedText
from app.db.models.enums import AiJobType, DocumentStatus
from app.db.session import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        documents = list(
            db.scalars(
                select(Document).where(
                    Document.status == DocumentStatus.ACTIVE,
                    Document.current_version_id.is_not(None),
                )
            )
        )

        repository = AiJobRepository(db)
        enqueued = 0
        skipped = 0
        for document in documents:
            version_id = document.current_version_id
            assert version_id is not None  # filtered by the query above
            already_queued = db.scalar(
                select(AiJob.id).where(
                    AiJob.document_version_id == version_id, AiJob.job_type == AiJobType.EXTRACT
                )
            )
            already_extracted = db.scalar(
                select(DocumentExtractedText.id).where(DocumentExtractedText.document_version_id == version_id)
            )
            if already_queued or already_extracted:
                skipped += 1
                continue
            repository.enqueue(job_type=AiJobType.EXTRACT, document_version_id=version_id)
            enqueued += 1

        db.commit()
        print(f"Enqueued {enqueued} extraction job(s), skipped {skipped} already-covered document(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
