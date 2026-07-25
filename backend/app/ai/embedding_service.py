from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.embedding_port import EmbeddingProvider, EmbeddingProviderError
from app.ai.embedding_repository import DocumentVectorEmbeddingRepository
from app.core.config import get_settings
from app.db.models import AiJob, DocumentVersion
from app.db.models.enums import AiAnalysisStatus, ExtractionStatus
from app.storage.local_adapter import LocalFileSystemStorage
from app.text_extraction.repository import DocumentExtractedTextRepository


class EmbeddingGenerationService:
    """The AiJobType.GENERATE_EMBEDDING handler — Similar Document Detection
    track. Matches ai_jobs.worker.JobHandler exactly, same shape as
    MetadataGenerationService (same DocumentVersion lookup, same
    extracted-text-required guard, same storage read, same
    try/except-and-re-raise around the provider call). Enqueued by
    TextExtractionService itself on successful extraction, independently of
    AiJobType.GENERATE_METADATA — neither job depends on the other's
    outcome."""

    def __init__(self, provider: EmbeddingProvider, storage: LocalFileSystemStorage, *, model_name: str) -> None:
        self.provider = provider
        self.storage = storage
        self.model_name = model_name

    def process_job(self, db: Session, job: AiJob) -> None:
        version = db.get(DocumentVersion, job.document_version_id)
        if version is None:
            # Parent hard-deleted between enqueue and claim — same no-op
            # convention as TextExtractionService/MetadataGenerationService.
            return

        extracted = DocumentExtractedTextRepository(db).get_by_version_id(version.id)
        row = DocumentVectorEmbeddingRepository(db).get_or_create(version.id)

        if extracted is None or extracted.status != ExtractionStatus.SUCCEEDED or not extracted.char_count:
            row.status = AiAnalysisStatus.SKIPPED
            row.error_message = "No usable extracted text for this version."
            row.generated_at = datetime.now(timezone.utc)
            db.commit()
            return

        assert extracted.extracted_text_path is not None
        with self.storage.open_for_read(extracted.extracted_text_path) as stream:
            full_text = stream.read().decode("utf-8", errors="replace")

        settings = get_settings()
        truncated_text = full_text[: settings.ai_embedding_max_chars]

        try:
            response = self.provider.generate_embedding(text=truncated_text, task_type="SEMANTIC_SIMILARITY")
        except EmbeddingProviderError as exc:
            # Never write embedding/embedding_model on failure — only the
            # execution metadata needed for observability. Re-raised so the
            # worker also marks the AiJob failed and applies its own backoff.
            row.status = AiAnalysisStatus.FAILED
            row.embedding_model = self.model_name
            row.input_char_count = len(truncated_text)
            row.error_message = str(exc)[:2000]
            row.generated_at = datetime.now(timezone.utc)
            db.commit()
            raise

        row.status = AiAnalysisStatus.SUCCEEDED
        row.embedding = response.vector
        row.embedding_model = response.model
        row.embedding_dimension = response.dimension
        row.input_char_count = len(truncated_text)
        row.latency_ms = response.latency_ms
        row.retry_count = response.retry_count
        row.error_message = None
        row.generated_at = datetime.now(timezone.utc)
        db.commit()
