import io
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import AiJob, DocumentVersion
from app.db.models.enums import AiJobType, ExtractionStatus
from app.storage.local_adapter import LocalFileSystemStorage
from app.text_extraction.registry import get_extractor
from app.text_extraction.repository import DocumentExtractedTextRepository
from app.utils.file_validation import get_extension


class TextExtractionService:
    """The AiJobType.EXTRACT handler — the only place that ties the pure
    `text_extraction/extractors/` together with storage and the DB. Matches
    the `ai_jobs.worker.JobHandler` signature exactly, so it's registered
    directly as `{AiJobType.EXTRACT: TextExtractionService(storage).process_job}`."""

    def __init__(self, storage: LocalFileSystemStorage) -> None:
        self.storage = storage

    def process_job(self, db: Session, job: AiJob) -> None:
        version = db.get(DocumentVersion, job.document_version_id)
        if version is None:
            # The parent document was hard-deleted between enqueue and claim —
            # cascade already removed this job's row's reason to exist.
            # Nothing to do; not a failure.
            return

        repository = DocumentExtractedTextRepository(db)
        row = repository.get_or_create(version.id)

        extension = get_extension(version.original_filename)
        dispatch = get_extractor(extension)
        if dispatch is None:
            row.status = ExtractionStatus.UNSUPPORTED
            row.extraction_method = None
            row.extracted_text_path = None
            row.char_count = None
            row.error_message = f"No extractor available for .{extension} files."
            row.extracted_at = datetime.now(timezone.utc)
            db.commit()
            return

        extractor, method = dispatch
        with self.storage.open_for_read(version.storage_path) as stream:
            result = extractor.extract(stream)

        text_storage_path = f"{version.storage_path}.txt"
        temp_path = self.storage.save_temp(io.BytesIO(result.text.encode("utf-8")))
        self.storage.commit(temp_path, text_storage_path)

        row.status = ExtractionStatus.SUCCEEDED
        row.extraction_method = method
        row.extracted_text_path = text_storage_path
        row.char_count = result.char_count
        row.error_message = None
        row.extracted_at = datetime.now(timezone.utc)

        # AI feature track (Phase 2): chained rather than enqueued unconditionally
        # at upload time like EXTRACT — no point paying for a model call against
        # a document with no usable text yet, and this only fires once text
        # genuinely exists.
        if result.char_count > 0:
            db.add(AiJob(job_type=AiJobType.GENERATE_METADATA, document_version_id=version.id))

        db.commit()
