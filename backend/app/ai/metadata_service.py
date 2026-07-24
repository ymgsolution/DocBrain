from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.analysis_repository import AiDocumentAnalysisRepository
from app.ai.port import AIProvider, AIProviderError
from app.ai.prompts.registry import get_prompt
from app.ai.schemas import MetadataSuggestion
from app.core.config import get_settings
from app.db.models import AiJob, Document, DocumentVersion
from app.db.models.enums import AiAnalysisStatus, ExtractionStatus
from app.storage.local_adapter import LocalFileSystemStorage
from app.text_extraction.repository import DocumentExtractedTextRepository

_PROMPT_NAME = "metadata_generation"


class MetadataGenerationService:
    """The AiJobType.GENERATE_METADATA handler — shadow mode only, nothing
    reads ai_document_analysis from any user-facing response yet. Matches
    ai_jobs.worker.JobHandler exactly, same shape as TextExtractionService.
    Enqueued by TextExtractionService itself on successful extraction, not
    at upload time — no point paying for a model call against a document
    that has no usable text yet (see the SKIPPED path below for the same
    reasoning applied defensively, in case a job is ever enqueued before
    extraction finishes)."""

    def __init__(self, provider: AIProvider, storage: LocalFileSystemStorage, *, model_name: str) -> None:
        self.provider = provider
        self.storage = storage
        self.model_name = model_name

    def process_job(self, db: Session, job: AiJob) -> None:
        version = db.get(DocumentVersion, job.document_version_id)
        if version is None:
            # Parent hard-deleted between enqueue and claim — same no-op
            # convention as TextExtractionService.
            return

        extracted = DocumentExtractedTextRepository(db).get_by_version_id(version.id)
        row = AiDocumentAnalysisRepository(db).get_or_create(version.id)

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
        truncated_text = full_text[: settings.ai_max_extracted_text_chars]

        document = db.get(Document, version.document_id)
        title = document.title if document is not None else version.original_filename

        prompt = get_prompt(_PROMPT_NAME)
        user_prompt = prompt.render_user(title=title, extracted_text=truncated_text)

        try:
            response = self.provider.generate_structured(
                system_prompt=prompt.system,
                user_prompt=user_prompt,
                response_schema=MetadataSuggestion,
                timeout_seconds=settings.ai_request_timeout_seconds,
            )
        except AIProviderError as exc:
            # Never write suggested_*/raw_response on failure — only the
            # execution metadata needed for observability. Re-raised so the
            # worker also marks the AiJob failed and applies its own backoff.
            row.status = AiAnalysisStatus.FAILED
            row.model_name = self.model_name
            row.prompt_name = prompt.name
            row.prompt_version = prompt.version
            row.input_char_count = len(truncated_text)
            row.error_message = str(exc)[:2000]
            row.generated_at = datetime.now(timezone.utc)
            db.commit()
            raise

        suggestion = response.data
        assert isinstance(suggestion, MetadataSuggestion)

        row.status = AiAnalysisStatus.SUCCEEDED
        row.suggested_title = suggestion.title
        # Reuses the existing suggested_description column as the summary
        # field — scoped to exactly 3 demo features (title/summary/tags), no
        # schema change needed. suggested_category/keywords/confidence_score
        # are simply left unset.
        row.suggested_description = suggestion.summary
        row.suggested_tags = suggestion.tags
        row.raw_response = response.raw_text
        row.model_name = response.model
        row.prompt_name = prompt.name
        row.prompt_version = prompt.version
        row.input_char_count = len(truncated_text)
        row.prompt_tokens = response.usage.prompt_tokens
        row.completion_tokens = response.usage.completion_tokens
        row.total_tokens = response.usage.total_tokens
        row.latency_ms = response.latency_ms
        row.retry_count = response.retry_count
        row.error_message = None
        row.generated_at = datetime.now(timezone.utc)
        db.commit()
