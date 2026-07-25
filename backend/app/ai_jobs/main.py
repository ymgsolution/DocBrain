"""The AI worker's runnable entrypoint: `uv run python -m app.ai_jobs.main`.

Its own process — never imported by app/main.py or run inside a FastAPI
request. Shares the same Postgres connection config as the API (via
app/db/session.py's SessionLocal) but not the request path, so a slow or
failing extraction never affects API latency.
"""

import logging

from app.ai.embedding_service import EmbeddingGenerationService
from app.ai.gemini_embedding_provider import GeminiEmbeddingProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.metadata_service import MetadataGenerationService
from app.ai_jobs.worker import JobHandler, run_forever
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.models.enums import AiJobType
from app.storage.factory import get_storage
from app.text_extraction.service import TextExtractionService

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    configure_logging()
    settings = get_settings()
    storage = get_storage()

    extraction_service = TextExtractionService(storage)
    handlers: dict[AiJobType, JobHandler] = {AiJobType.EXTRACT: extraction_service.process_job}

    # GENERATE_METADATA is only registered when a Gemini key is configured —
    # extraction must keep working even without one. Jobs enqueued with no
    # handler registered just sit PENDING until a worker with a key claims
    # them (same "silently queue up" behavior already documented for a down
    # worker in PROJECT_STATUS.md).
    if settings.gemini_api_key:
        provider = GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            max_retries=settings.ai_max_retries,
        )
        metadata_service = MetadataGenerationService(provider, storage, model_name=settings.gemini_model)
        handlers[AiJobType.GENERATE_METADATA] = metadata_service.process_job

        # Similar Document Detection track — same gemini_api_key gate, same
        # "just sits PENDING with no handler" fallback as GENERATE_METADATA.
        # Independent GeminiEmbeddingProvider/EmbeddingGenerationService, not
        # coupled to the metadata service above.
        embedding_provider = GeminiEmbeddingProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_embedding_model,
            max_retries=settings.ai_max_retries,
            output_dimensionality=settings.ai_embedding_dimensions,
        )
        embedding_service = EmbeddingGenerationService(
            embedding_provider, storage, model_name=settings.gemini_embedding_model
        )
        handlers[AiJobType.GENERATE_EMBEDDING] = embedding_service.process_job
    else:
        logger.warning("GEMINI_API_KEY not configured — metadata generation and embedding jobs will not be processed.")

    run_forever(handlers=handlers)
